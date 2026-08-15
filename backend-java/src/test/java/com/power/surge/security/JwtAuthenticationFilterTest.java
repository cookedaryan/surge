package com.power.surge.security;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.repository.UserRepository;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * The filter used to trust the bearer token outright and never read the database. Because tokens
 * last a day and cannot be recalled, every administrative action was cosmetic against anyone
 * already holding one — a disabled account kept working, a demoted administrator kept
 * administering, and a password reset locked nobody out.
 */
@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    private static final String SECRET = "a-test-signing-key-that-is-at-least-32-bytes-long";

    @Mock
    private UserRepository userRepository;

    private JwtTokenProvider tokenProvider;
    private JwtAuthenticationFilter filter;

    @BeforeEach
    void setUp() {
        tokenProvider = new JwtTokenProvider(SECRET, 86_400_000L);
        filter = new JwtAuthenticationFilter(tokenProvider, userRepository);
        SecurityContextHolder.clearContext();
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private Authentication runFilterWithTokenFor(User user) throws Exception {
        String token = tokenProvider.generateToken(UUID.randomUUID(), user.getUsername(), user.getRole());
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + token);
        FilterChain chain = (req, res) -> { };
        filter.doFilter(request, new MockHttpServletResponse(), chain);
        return SecurityContextHolder.getContext().getAuthentication();
    }

    @Test
    void anEnabledUserIsAuthenticated() throws Exception {
        User user = new User("engineer", "e@surge.energy", "hash", UserRole.ROLE_ENGINEER);
        when(userRepository.findByUsername(anyString())).thenReturn(Optional.of(user));

        Authentication auth = runFilterWithTokenFor(user);

        assertThat(auth).isNotNull();
        assertThat(auth.getAuthorities()).extracting(Object::toString).containsExactly("ROLE_ENGINEER");
    }

    @Test
    void aDisabledAccountIsRejectedEvenWithAValidToken() throws Exception {
        User user = new User("engineer", "e@surge.energy", "hash", UserRole.ROLE_ENGINEER);
        String token = tokenProvider.generateToken(UUID.randomUUID(), user.getUsername(), user.getRole());
        user.setEnabled(false);
        when(userRepository.findByUsername(anyString())).thenReturn(Optional.of(user));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + token);
        filter.doFilter(request, new MockHttpServletResponse(), (req, res) -> { });

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }

    @Test
    void anAccountDeletedSinceTheTokenWasIssuedIsRejected() throws Exception {
        User user = new User("ghost", "g@surge.energy", "hash", UserRole.ROLE_ADMIN);
        when(userRepository.findByUsername(anyString())).thenReturn(Optional.empty());

        assertThat(runFilterWithTokenFor(user)).isNull();
    }

    /**
     * The token still carries ROLE_ADMIN; the row says otherwise. The row wins, otherwise a
     * demotion would not take effect until the old token expired a day later.
     */
    @Test
    void authoritiesComeFromTheRowRatherThanTheTokenClaim() throws Exception {
        User user = new User("demoted", "d@surge.energy", "hash", UserRole.ROLE_ADMIN);
        String adminToken = tokenProvider.generateToken(UUID.randomUUID(), user.getUsername(), UserRole.ROLE_ADMIN);
        assertThat(tokenProvider.getRoleFromToken(adminToken)).isEqualTo("ROLE_ADMIN");

        user.setRole(UserRole.ROLE_VIEWER);
        // Re-issued at the same instant as the demotion so the staleness rule cannot be what
        // rejects it — this test is about the authority, not about expiry.
        String token = tokenProvider.generateToken(UUID.randomUUID(), user.getUsername(), UserRole.ROLE_ADMIN);
        when(userRepository.findByUsername(anyString())).thenReturn(Optional.of(user));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + token);
        filter.doFilter(request, new MockHttpServletResponse(), (req, res) -> { });

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        assertThat(auth).isNotNull();
        assertThat(auth.getAuthorities()).extracting(Object::toString).containsExactly("ROLE_VIEWER");
    }

    @Test
    void aTokenIssuedBeforeAPasswordResetIsRejected() throws Exception {
        User user = new User("engineer", "e@surge.energy", "hash", UserRole.ROLE_ENGINEER);
        String oldToken = tokenProvider.generateToken(UUID.randomUUID(), user.getUsername(), user.getRole());

        // Backdate the token by a couple of seconds, then reset the password. Real resets happen
        // long after the session started; the shift just clears the one-second comparison window.
        Thread.sleep(1100);
        user.setPasswordHash("new-hash");
        when(userRepository.findByUsername(anyString())).thenReturn(Optional.of(user));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + oldToken);
        filter.doFilter(request, new MockHttpServletResponse(), (req, res) -> { });

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }
}

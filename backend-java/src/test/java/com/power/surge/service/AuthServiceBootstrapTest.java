package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.repository.UserRepository;
import com.power.surge.security.JwtTokenProvider;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Guards the bootstrap-administrator contract.
 *
 * <p>The previous implementation re-encoded the seeded password on every startup. That silently
 * reverted any credential change on the next restart, which would have made an administrator-driven
 * password reset appear to work and then quietly undo itself.
 */
@ExtendWith(MockitoExtension.class)
class AuthServiceBootstrapTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private JwtTokenProvider tokenProvider;

    @Mock
    private AuditLogService auditLogService;

    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
    private AuthService authService;

    @BeforeEach
    void setUp() {
        authService = new AuthService(userRepository, passwordEncoder, tokenProvider, auditLogService);
    }

    @Test
    void createsTheAdministratorWhenTheDatabaseIsFresh() {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.empty());

        authService.seedBootstrapAdmin("admin", "admin@surge.energy", "s3cret-bootstrap");

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        User created = captor.getValue();

        assertThat(created.getUsername()).isEqualTo("admin");
        assertThat(created.getRole()).isEqualTo(UserRole.ROLE_ADMIN);
        assertThat(created.getPasswordHash()).isNotEqualTo("s3cret-bootstrap");
        assertThat(passwordEncoder.matches("s3cret-bootstrap", created.getPasswordHash())).isTrue();
    }

    /** The regression that matters: a restart must not resurrect the seeded password. */
    @Test
    void neverOverwritesAnExistingAdministratorPassword() {
        User existing = new User("admin", "admin@surge.energy",
                passwordEncoder.encode("password-the-operator-chose"), UserRole.ROLE_ADMIN);
        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(existing));

        authService.seedBootstrapAdmin("admin", "admin@surge.energy", "the-original-seed");

        verify(userRepository, never()).save(org.mockito.ArgumentMatchers.any(User.class));
        assertThat(passwordEncoder.matches("password-the-operator-chose", existing.getPasswordHash()))
                .as("the operator's password must survive a restart")
                .isTrue();
        assertThat(passwordEncoder.matches("the-original-seed", existing.getPasswordHash()))
                .as("the seed password must not be reinstated")
                .isFalse();
    }

    @Test
    void honoursAConfiguredAdministratorUsername() {
        when(userRepository.findByUsername("ops-lead")).thenReturn(Optional.empty());

        authService.seedBootstrapAdmin("ops-lead", "ops@example.com", "another-secret");

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        assertThat(captor.getValue().getUsername()).isEqualTo("ops-lead");
        assertThat(captor.getValue().getEmail()).isEqualTo("ops@example.com");
    }

    // --- the password the first administrator gets -----------------------
    //
    // This used to default to "admin" and log a warning when it was used. That did not work: an
    // instance seeded that way was briefly reachable from the internet with administrator access
    // while the warning sat unread in container logs. Seeding now refuses instead.

    @Test
    void refusesToSeedAnAdministratorWithNoPassword() {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> authService.seedBootstrapAdmin("admin", "admin@surge.energy", ""))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("SURGE_BOOTSTRAP_ADMIN_PASSWORD");
        assertThatThrownBy(() -> authService.seedBootstrapAdmin("admin", "admin@surge.energy", null))
                .isInstanceOf(IllegalStateException.class);

        verify(userRepository, never()).save(org.mockito.ArgumentMatchers.any(User.class));
    }

    @Test
    void refusesThePasswordThisProjectUsedToDefaultTo() {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.empty());

        // Published in this repository's history, so it is no better than no password at all.
        assertThatThrownBy(() -> authService.seedBootstrapAdmin("admin", "admin@surge.energy", "admin"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("history");

        verify(userRepository, never()).save(org.mockito.ArgumentMatchers.any(User.class));
    }

    @Test
    void refusesAPasswordShorterThanEveryOtherAccountMustHave() {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> authService.seedBootstrapAdmin("admin", "admin@surge.energy", "short1"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("8 characters");
    }

    /**
     * The requirement lands only where the risk is. An existing deployment restarting with no
     * bootstrap password configured has no account to create and must start normally — otherwise
     * this change would take running systems down rather than protect new ones.
     */
    @Test
    void startsNormallyWithNoPasswordWhenTheAdministratorAlreadyExists() {
        User existing = new User("admin", "admin@surge.energy",
                passwordEncoder.encode("password-the-operator-chose"), UserRole.ROLE_ADMIN);
        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(existing));

        authService.seedBootstrapAdmin("admin", "admin@surge.energy", "");

        verify(userRepository, never()).save(org.mockito.ArgumentMatchers.any(User.class));
    }
}

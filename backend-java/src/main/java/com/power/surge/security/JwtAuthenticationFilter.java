package com.power.surge.security;

import com.power.surge.domain.User;
import com.power.surge.repository.UserRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

/**
 * Authenticates a request from its bearer token, then checks that token against the account it
 * names.
 *
 * <p>This filter used to trust the token entirely and never read the database. A token is valid for
 * a day and cannot be recalled, so every administrative action was cosmetic for anyone already
 * holding one: a disabled account kept working, a demoted administrator kept administering, and a
 * password reset locked nobody out. For a system whose access control *is* the admin panel, that
 * made the panel decorative.
 *
 * <p>The cost is one indexed lookup per authenticated request, which at this system's scale is not
 * worth trading away for the guarantee.
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider tokenProvider;
    private final UserRepository userRepository;

    public JwtAuthenticationFilter(JwtTokenProvider tokenProvider, UserRepository userRepository) {
        this.tokenProvider = tokenProvider;
        this.userRepository = userRepository;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String token = getJwtFromRequest(request);

        if (StringUtils.hasText(token) && tokenProvider.validateToken(token)) {
            authenticate(token, request);
        }

        filterChain.doFilter(request, response);
    }

    /**
     * Leaves the context unauthenticated whenever the token no longer reflects the account. The
     * request then fails as anonymous, which the entry point turns into a 401.
     */
    private void authenticate(String token, HttpServletRequest request) {
        Optional<User> found = userRepository.findByUsername(tokenProvider.getUsernameFromToken(token));
        if (found.isEmpty()) {
            return;
        }
        User user = found.get();
        if (!user.isEnabled() || isStale(token, user)) {
            return;
        }

        // The role comes from the row, not from the token's claim: a demotion has to bite
        // immediately, and the claim reflects whatever was true when the token was minted.
        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                user.getUsername(),
                null,
                List.of(new SimpleGrantedAuthority(user.getRole().name()))
        );
        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
        SecurityContextHolder.getContext().setAuthentication(authentication);
    }

    /**
     * True when the token predates the account's last credentials or privilege change.
     *
     * <p>A token's issued-at only has second precision, so the comparison is made at that
     * granularity. A token minted in the same second as the change survives — a window of under a
     * second, and closing it would instead risk rejecting freshly issued tokens.
     */
    private boolean isStale(String token, User user) {
        Instant issuedAt = tokenProvider.getIssuedAtFromToken(token);
        Instant changedAt = user.getCredentialsUpdatedAt();
        return changedAt != null && issuedAt.isBefore(changedAt.truncatedTo(ChronoUnit.SECONDS));
    }

    private String getJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}

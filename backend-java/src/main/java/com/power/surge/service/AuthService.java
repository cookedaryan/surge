package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.dto.auth.AuthResponse;
import com.power.surge.dto.auth.LoginRequest;
import com.power.surge.dto.auth.RegisterRequest;
import com.power.surge.repository.UserRepository;
import com.power.surge.security.JwtTokenProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    /** Local-development fallback only; a deployed instance must override this. */
    public static final String DEFAULT_BOOTSTRAP_PASSWORD = "admin";

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final AuditLogService auditLogService;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtTokenProvider tokenProvider,
            AuditLogService auditLogService
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.tokenProvider = tokenProvider;
        this.auditLogService = auditLogService;
    }

    /**
     * Creates the bootstrap administrator when it does not already exist.
     *
     * <p>This deliberately never touches an existing account. The previous implementation
     * re-encoded the password on every startup, which meant any credential change — including one
     * made through the admin flow — was silently reverted the next time the backend restarted.
     *
     * <p>Credentials come from configuration so they are not baked into the source tree. The
     * defaults exist only to keep a fresh local checkout usable, and are logged as a warning so an
     * unchanged default cannot go unnoticed in a deployed environment.
     */
    @Transactional
    public void seedBootstrapAdmin(String username, String email, String password) {
        if (userRepository.findByUsername(username).isPresent()) {
            log.info("Bootstrap administrator '{}' already exists; leaving its credentials untouched.", username);
            return;
        }
        userRepository.save(new User(username, email, passwordEncoder.encode(password), UserRole.ROLE_ADMIN));
        log.info("Created bootstrap administrator '{}'.", username);
        if (DEFAULT_BOOTSTRAP_PASSWORD.equals(password)) {
            log.warn("Bootstrap administrator '{}' is using the built-in default password. "
                    + "Set SURGE_BOOTSTRAP_ADMIN_PASSWORD before exposing this instance to anyone else.", username);
        }
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new IllegalArgumentException("Username is already taken.");
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("Email is already registered.");
        }

        String encodedPassword = passwordEncoder.encode(request.password());
        UserRole role = request.role() != null ? request.role() : UserRole.ROLE_ENGINEER;

        User user = new User(request.username(), request.email(), encodedPassword, role);
        user = userRepository.save(user);

        auditLogService.recordAudit(user.getUsername(), "USER_REGISTERED", "USER", user.getId().toString(), "New user account created");

        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }

    @Transactional
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new IllegalArgumentException("Invalid username or password."));

        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new IllegalArgumentException("Invalid username or password.");
        }

        auditLogService.recordAudit(user.getUsername(), "USER_LOGIN", "USER", user.getId().toString(), "Successful user authentication");

        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }

    public AuthResponse getCurrentUser(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + username));
        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }
}

package com.power.surge.config;

import com.power.surge.security.JwtAuthenticationFilter;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // A denied request calls sendError(), which makes the container re-dispatch
                        // to /error through this same chain. That dispatch carries no credentials,
                        // so without this rule it is itself rejected and the entry point overwrites
                        // the real 403 with a 401 — telling an authenticated user they are not
                        // logged in. MockMvc performs no ERROR dispatch, so only a running server
                        // shows this.
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        // Only signing in and liveness probes may be reached anonymously.
                        .requestMatchers(
                                "/api/v1/auth/login",
                                "/api/v1/health",
                                "/actuator/health",
                                "/actuator/health/**"
                        ).permitAll()
                        // Accounts are provisioned by an administrator, never self-served. Leaving
                        // this open would make every other rule here pointless: anyone could
                        // register, receive a valid token, and walk back in through the front door.
                        .requestMatchers("/api/v1/auth/register").hasRole("ADMIN")
                        // Everything else, including the job-progress SSE stream, requires a token.
                        // The browser EventSource API cannot attach an Authorization header, so the
                        // client streams progress over fetch instead (see listenJobProgress). A JWT
                        // must never be passed as a query parameter to work around this: it would
                        // end up in access logs, browser history and referrer headers.
                        .anyRequest().authenticated()
                )
                // Without this, Spring answers an unauthenticated request with 403, which tells a
                // client "you may not do this" when the truth is "you have not identified
                // yourself". The distinction is what lets the UI send an expired session back to
                // the login screen instead of showing a permission error.
                .exceptionHandling(handling -> handling
                        .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}

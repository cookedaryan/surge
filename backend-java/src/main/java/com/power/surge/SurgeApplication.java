package com.power.surge;

import com.power.surge.service.AuthService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class SurgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(SurgeApplication.class, args);
    }

    /**
     * Ensures a single administrator account exists so a fresh database is usable. Every other
     * account is created by an administrator through {@code POST /api/v1/auth/register}; this
     * runner only bootstraps the first one and never overwrites existing credentials.
     */
    @Bean
    public CommandLineRunner initDatabase(
            AuthService authService,
            @Value("${surge.bootstrap-admin.username:admin}") String username,
            @Value("${surge.bootstrap-admin.email:admin@surge.energy}") String email,
            // No default. An unset password is only an error if an account actually needs
            // creating, so an existing deployment still starts unconfigured while a fresh database
            // refuses to seed an administrator nobody chose the password for.
            @Value("${surge.bootstrap-admin.password:}") String password
    ) {
        return args -> authService.seedBootstrapAdmin(username, email, password);
    }
}

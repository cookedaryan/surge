package com.power.surge;

import com.power.surge.service.AuthService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class SurgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(SurgeApplication.class, args);
    }

    @Bean
    public CommandLineRunner initDatabase(AuthService authService) {
        return args -> {
            authService.seedDemoUsers();
        };
    }
}
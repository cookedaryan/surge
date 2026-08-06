package com.power.surge;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@SpringBootApplication
@EntityScan(basePackages = "com.power.surge.domain")
@EnableJpaRepositories(basePackages = "com.power.surge.repository")
public class SurgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(SurgeApplication.class, args);
    }
}
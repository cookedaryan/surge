package com.power.surge.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.security.task.DelegatingSecurityContextAsyncTaskExecutor;

import java.util.concurrent.ThreadPoolExecutor;

@Configuration
@EnableAsync
public class AsyncConfig {

    public static final String OPTIMIZATION_EXECUTOR = "optimizationExecutor";

    /**
     * Runs optimisation jobs off the request thread.
     *
     * <p>A run takes tens of seconds on real survey data, so executing it inside the HTTP request
     * held the connection open for the duration and let a handful of concurrent runs exhaust the
     * servlet pool.
     *
     * <p>Wrapped in {@link DelegatingSecurityContextAsyncTaskExecutor} so the authenticated
     * principal travels with the task. Without it the security context is empty on the worker
     * thread and every audit entry a job writes would be attributed to "anonymous" — the log would
     * still be written, and would still be wrong.
     *
     * <p>The pool is deliberately small: each task drives a CPU-heavy solve in the Python service,
     * so queueing work is preferable to running more of it at once. An overflowing queue aborts
     * rather than running the task on the caller, which would put us back on the request thread.
     */
    @Bean(name = OPTIMIZATION_EXECUTOR)
    public DelegatingSecurityContextAsyncTaskExecutor optimizationExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(4);
        executor.setQueueCapacity(20);
        executor.setThreadNamePrefix("surge-optimise-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        // Let an in-flight solve finish on shutdown rather than leaving a job stuck in RUNNING.
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(120);
        executor.initialize();
        return new DelegatingSecurityContextAsyncTaskExecutor(executor);
    }
}

package com.power.surge.service;

import com.power.surge.domain.JobStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class SseProgressServiceTest {

    private SseProgressService sseProgressService;

    @BeforeEach
    void setUp() {
        sseProgressService = new SseProgressService();
    }

    @Test
    void registerEmitter_registersAndTracksEmitter() {
        UUID jobId = UUID.randomUUID();
        SseEmitter emitter = sseProgressService.registerEmitter(jobId);

        assertThat(emitter).isNotNull();
        assertThat(sseProgressService.getActiveEmitterCount(jobId)).isEqualTo(1);
    }

    @Test
    void emitProgress_sendsEventToActiveEmitters() {
        UUID jobId = UUID.randomUUID();
        sseProgressService.registerEmitter(jobId);

        sseProgressService.emitProgress(jobId, 50, "Halfway done", JobStatus.RUNNING);

        assertThat(sseProgressService.getActiveEmitterCount(jobId)).isEqualTo(1);
    }

    @Test
    void completeProgress_completesAndCleansEmitters() {
        UUID jobId = UUID.randomUUID();
        sseProgressService.registerEmitter(jobId);

        sseProgressService.completeProgress(jobId, "Finished", true);

        assertThat(sseProgressService.getActiveEmitterCount(jobId)).isEqualTo(0);
    }
}

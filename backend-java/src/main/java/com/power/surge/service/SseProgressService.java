package com.power.surge.service;

import com.power.surge.domain.JobStatus;
import com.power.surge.dto.job.JobProgressEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class SseProgressService {

    private static final Logger log = LoggerFactory.getLogger(SseProgressService.class);
    private static final Long SSE_TIMEOUT = 300_000L; // 5 minutes timeout

    private final Map<UUID, List<SseEmitter>> emittersMap = new ConcurrentHashMap<>();

    public SseEmitter registerEmitter(UUID jobId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);
        emittersMap.computeIfAbsent(jobId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        Runnable cleanup = () -> removeEmitter(jobId, emitter);
        emitter.onCompletion(cleanup);
        emitter.onTimeout(cleanup);
        emitter.onError(e -> cleanup.run());

        // Send initial connection event
        try {
            emitter.send(SseEmitter.event()
                    .name("progress")
                    .data(JobProgressEvent.of(jobId, JobStatus.PENDING, 0, "Connected to job progress stream")));
        } catch (IOException e) {
            log.warn("Failed to send initial SSE connection event for job {}", jobId, e);
            removeEmitter(jobId, emitter);
        }

        return emitter;
    }

    public void emitProgress(UUID jobId, int progressPercent, String message, JobStatus status) {
        List<SseEmitter> emitters = emittersMap.get(jobId);
        if (emitters == null || emitters.isEmpty()) {
            return;
        }

        JobProgressEvent event = JobProgressEvent.of(jobId, status, progressPercent, message);

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("progress")
                        .data(event));
            } catch (Exception e) {
                log.debug("Failed to send SSE progress event for job {}, removing emitter", jobId);
                removeEmitter(jobId, emitter);
            }
        }
    }

    public void completeProgress(UUID jobId, String message, boolean success) {
        JobStatus status = success ? JobStatus.COMPLETED : JobStatus.FAILED;
        int percent = success ? 100 : 100;
        emitProgress(jobId, percent, message, status);

        List<SseEmitter> emitters = emittersMap.remove(jobId);
        if (emitters != null) {
            for (SseEmitter emitter : emitters) {
                try {
                    emitter.complete();
                } catch (Exception e) {
                    log.debug("Error completing SseEmitter for job {}", jobId);
                }
            }
        }
    }

    private void removeEmitter(UUID jobId, SseEmitter emitter) {
        List<SseEmitter> list = emittersMap.get(jobId);
        if (list != null) {
            list.remove(emitter);
            if (list.isEmpty()) {
                emittersMap.remove(jobId);
            }
        }
    }

    public int getActiveEmitterCount(UUID jobId) {
        List<SseEmitter> list = emittersMap.get(jobId);
        return list != null ? list.size() : 0;
    }
}

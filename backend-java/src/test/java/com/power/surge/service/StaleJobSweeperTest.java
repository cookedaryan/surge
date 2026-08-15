package com.power.surge.service;

import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import com.power.surge.domain.Project;
import com.power.surge.repository.OptimizationJobRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StaleJobSweeperTest {

    @Mock
    private OptimizationJobRepository jobRepository;

    private static OptimizationJob job(JobStatus status) {
        OptimizationJob job = new OptimizationJob(new Project("P", null), "A*", null, null, null, null);
        if (status == JobStatus.RUNNING) {
            job.markRunning();
        }
        return job;
    }

    /**
     * Work lives in an in-memory executor while its status lives in the database. A crash leaves
     * the row claiming RUNNING with nothing left to finish it.
     */
    @Test
    void failsJobsLeftRunningByAPreviousProcess() {
        OptimizationJob orphan = job(JobStatus.RUNNING);
        when(jobRepository.findAllByStatus(JobStatus.RUNNING)).thenReturn(new ArrayList<>(List.of(orphan)));
        when(jobRepository.findAllByStatus(JobStatus.PENDING)).thenReturn(new ArrayList<>());

        new StaleJobSweeper(jobRepository).failJobsOrphanedByRestart();

        assertThat(orphan.getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(orphan.getErrorMessage()).contains("restarted");
    }

    /** A job queued but never picked up is equally orphaned — no worker survived to claim it. */
    @Test
    void failsJobsStillQueuedFromAPreviousProcess() {
        OptimizationJob queued = job(JobStatus.PENDING);
        when(jobRepository.findAllByStatus(JobStatus.RUNNING)).thenReturn(new ArrayList<>());
        when(jobRepository.findAllByStatus(JobStatus.PENDING)).thenReturn(new ArrayList<>(List.of(queued)));

        new StaleJobSweeper(jobRepository).failJobsOrphanedByRestart();

        ArgumentCaptor<List<OptimizationJob>> captor = ArgumentCaptor.forClass(List.class);
        verify(jobRepository).saveAll(captor.capture());
        assertThat(captor.getValue()).containsExactly(queued);
        assertThat(queued.getStatus()).isEqualTo(JobStatus.FAILED);
    }

    @Test
    void doesNothingWhenNoJobsWereInterrupted() {
        when(jobRepository.findAllByStatus(JobStatus.RUNNING)).thenReturn(new ArrayList<>());
        when(jobRepository.findAllByStatus(JobStatus.PENDING)).thenReturn(new ArrayList<>());

        new StaleJobSweeper(jobRepository).failJobsOrphanedByRestart();

        verify(jobRepository, never()).saveAll(org.mockito.ArgumentMatchers.anyList());
    }
}

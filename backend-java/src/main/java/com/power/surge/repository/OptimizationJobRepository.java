package com.power.surge.repository;

import com.power.surge.domain.JobStatus;
import com.power.surge.domain.OptimizationJob;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface OptimizationJobRepository extends JpaRepository<OptimizationJob, UUID> {

    List<OptimizationJob> findAllByProjectIdOrderByCreatedAtDesc(UUID projectId);

    List<OptimizationJob> findAllByStatus(JobStatus status);
}

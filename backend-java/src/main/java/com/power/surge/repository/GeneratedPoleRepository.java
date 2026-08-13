package com.power.surge.repository;

import com.power.surge.domain.GeneratedPole;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface GeneratedPoleRepository extends JpaRepository<GeneratedPole, UUID> {

    List<GeneratedPole> findAllByJobIdOrderByPoleIdentifierAsc(UUID jobId);
}

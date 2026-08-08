package com.power.surge.repository;

import com.power.surge.domain.GeneratedRoute;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface GeneratedRouteRepository extends JpaRepository<GeneratedRoute, UUID> {

    List<GeneratedRoute> findAllByJobIdOrderByFeederNameAsc(UUID jobId);
}

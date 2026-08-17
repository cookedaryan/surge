package com.power.surge.repository;

import com.power.surge.domain.CadastralParcel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface CadastralParcelRepository extends JpaRepository<CadastralParcel, UUID> {

    List<CadastralParcel> findAllByProjectIdOrderByParcelIdAsc(UUID projectId);

}

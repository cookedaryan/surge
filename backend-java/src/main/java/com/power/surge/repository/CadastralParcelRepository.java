package com.power.surge.repository;

import com.power.surge.domain.CadastralParcel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface CadastralParcelRepository extends JpaRepository<CadastralParcel, UUID> {

    List<CadastralParcel> findAllByProjectIdOrderByParcelIdAsc(UUID projectId);

    /**
     * Area of each parcel actually covered by the right-of-way corridor of a job's routes.
     *
     * <p>The corridor is the routes buffered by half the ROW width, and the answer is the area of
     * its intersection with the parcel — not the parcel's whole area, which is what land
     * compensation was previously being estimated from.
     *
     * <p>Every measurement goes through {@code ::geography} so PostGIS works on the ellipsoid and
     * returns real metres. Buffering the raw 4326 geometry would treat the width as degrees, and
     * multiplying a degree-based area by a fixed metres-per-degree constant is only valid on the
     * equator and along a meridian.
     *
     * <p>Parcels the corridor misses are returned with zero rather than omitted, so the report can
     * still list them as unaffected.
     *
     * @param halfWidthMeters half the ROW corridor width, in metres
     * @return rows of {@code [parcel_id, affected_area_m2]}, ordered by parcel id
     */
    @Query(value = """
            SELECT p.parcel_id AS parcel_id,
                   COALESCE(SUM(
                       ST_Area(
                           ST_Intersection(
                               ST_Buffer(r.route_path::geography, :halfWidthMeters)::geometry,
                               p.geometry
                           )::geography
                       )
                   ), 0) AS affected_area_m2
            FROM cadastral_parcels p
            LEFT JOIN generated_routes r
                   ON r.job_id = :jobId
                  AND r.route_path IS NOT NULL
                  AND ST_Intersects(
                          ST_Buffer(r.route_path::geography, :halfWidthMeters)::geometry,
                          p.geometry
                      )
            WHERE p.project_id = :projectId
            GROUP BY p.parcel_id
            ORDER BY p.parcel_id
            """, nativeQuery = true)
    List<Object[]> findRowCorridorAreaByParcel(
            @Param("projectId") UUID projectId,
            @Param("jobId") UUID jobId,
            @Param("halfWidthMeters") double halfWidthMeters
    );
}

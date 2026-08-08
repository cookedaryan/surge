package com.power.surge.domain;

import org.junit.jupiter.api.Test;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

class ProjectDomainTest {

    private final GeometryFactory wgs84GeometryFactory = new GeometryFactory(
            new PrecisionModel(),
            Project.WGS84_SRID
    );

    @Test
    void createsProjectAssetsWithWgs84Locations() {
        Project project = new Project("North Ridge Wind Farm", "MVP project");
        Point location = wgs84Point(77.2302, 28.6301);

        WtgLocation wtg = new WtgLocation(
                project,
                "WTG-001",
                new BigDecimal("3.000"),
                location
        );
        Substation substation = new Substation(project, "SUB-001", null, location);

        assertThat(wtg.getProject()).isSameAs(project);
        assertThat(wtg.getCapacityMw()).isEqualByComparingTo("3.000");
        assertThat(substation.getCapacityMw()).isNull();
        assertThat(substation.getLocation().getSRID()).isEqualTo(Project.WGS84_SRID);
    }

    @Test
    void rejectsInvalidWtgCapacity() {
        Project project = new Project("North Ridge Wind Farm", null);

        assertThatIllegalArgumentException().isThrownBy(() -> new WtgLocation(
                project,
                "WTG-001",
                BigDecimal.ZERO,
                wgs84Point(77.2302, 28.6301)
        )).withMessage("WTG capacity must be greater than zero.");
    }

    @Test
    void rejectsLocationsOutsideWgs84() {
        Project project = new Project("North Ridge Wind Farm", null);
        Point missingSrid = new GeometryFactory().createPoint(new Coordinate(77.2302, 28.6301));

        assertThatIllegalArgumentException().isThrownBy(() -> new Substation(
                project,
                "SUB-001",
                null,
                missingSrid
        )).withMessage("Substation location must use SRID 4326.");
    }

    private Point wgs84Point(double longitude, double latitude) {
        return wgs84GeometryFactory.createPoint(new Coordinate(longitude, latitude));
    }
}

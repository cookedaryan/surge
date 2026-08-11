package com.power.surge.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class KmzGeoJsonConverterTest {

    private KmzGeoJsonConverter converter;

    @BeforeEach
    void setUp() {
        converter = new KmzGeoJsonConverter();
    }

    private byte[] createKmz(String kmlContent, String kmlFileName) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            ZipEntry entry = new ZipEntry(kmlFileName);
            zos.putNextEntry(entry);
            zos.write(kmlContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return baos.toByteArray();
    }

    @Test
    void convertsKmzWithExtendedDataStyle1() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>WTG-001</name>
                      <Point>
                        <coordinates>77.2302,28.6301,15.0</coordinates>
                      </Point>
                      <ExtendedData>
                        <Data name="capacityMw">
                          <value>3.5</value>
                        </Data>
                      </ExtendedData>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "doc.kml");

        Map<String, Object> result = converter.convertToFeatureCollection(kmzBytes);
        assertThat(result).containsEntry("type", "FeatureCollection");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(1);

        Map<String, Object> feature = features.get(0);
        assertThat(feature).containsEntry("type", "Feature");

        @SuppressWarnings("unchecked")
        Map<String, Object> geometry = (Map<String, Object>) feature.get("geometry");
        assertThat(geometry).containsEntry("type", "Point");
        assertThat(geometry.get("coordinates")).isEqualTo(List.of(77.2302, 28.6301));

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) feature.get("properties");
        assertThat(properties).containsEntry("externalId", "WTG-001");
        assertThat(properties).containsEntry("capacityMw", "3.5");
    }

    @Test
    void convertsKmzWithExtendedDataStyle2() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>WTG-002</name>
                      <Point>
                        <coordinates>77.2500,28.6400</coordinates>
                      </Point>
                      <ExtendedData>
                        <SchemaData schemaUrl="#WtgSchema">
                          <SimpleData name="capacityMw">4.2</SimpleData>
                          <SimpleData name="manufacturer">Vestas</SimpleData>
                        </SchemaData>
                      </ExtendedData>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "wtg_locations.kml");

        Map<String, Object> result = converter.convertToFeatureCollection(kmzBytes);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(1);

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) features.get(0).get("properties");
        assertThat(properties).containsEntry("externalId", "WTG-002");
        assertThat(properties).containsEntry("capacityMw", "4.2");
        assertThat(properties).containsEntry("manufacturer", "Vestas");
    }

    @Test
    void convertsPlacemarkWithoutExtendedData() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>WTG-MIN</name>
                      <Point>
                        <coordinates>77.1000, 28.5000</coordinates>
                      </Point>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "doc.kml");

        Map<String, Object> result = converter.convertToFeatureCollection(kmzBytes);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(1);

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) features.get(0).get("properties");
        assertThat(properties).containsEntry("externalId", "WTG-MIN");
        assertThat(properties).doesNotContainKey("capacityMw");
    }

    @Test
    void convertsNestedFolderPlacemarks() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Folder>
                      <name>Phase 1</name>
                      <Folder>
                        <name>Sector A</name>
                        <Placemark>
                          <name>WTG-NESTED</name>
                          <Point>
                            <coordinates>77.1234,28.5678</coordinates>
                          </Point>
                        </Placemark>
                      </Folder>
                    </Folder>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "doc.kml");

        Map<String, Object> result = converter.convertToFeatureCollection(kmzBytes);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(1);

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) features.get(0).get("properties");
        assertThat(properties).containsEntry("externalId", "WTG-NESTED");

        // The enclosing folder names are the strongest classification signal in a survey export and
        // must survive conversion; the previous flat placemark scan discarded them.
        assertThat(properties).containsEntry("kmlFolder", "Sector A");
        assertThat(properties).containsEntry("kmlFolderPath", "Phase 1 / Sector A");
    }

    @Test
    void deduplicatesPlacemarksRepeatedAcrossNestedCopiesOfTheSameTree() throws Exception {
        // Google Earth exports routinely nest a copy of the whole tree under one of their own
        // folders. The reference Uravakonda file describes 303 assets across 903 placemarks.
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Folder>
                      <name>Approved</name>
                      <Placemark>
                        <name>KS67_S1</name>
                        <Point><coordinates>77.1234,28.5678</coordinates></Point>
                      </Placemark>
                    </Folder>
                    <Folder>
                      <name>My Places</name>
                      <Folder>
                        <name>Approved</name>
                        <Placemark>
                          <name>KS67_S1</name>
                          <Point><coordinates>77.1234,28.5678</coordinates></Point>
                        </Placemark>
                        <Placemark>
                          <name>KS 67 S1</name>
                          <Point><coordinates>77.1234,28.5678</coordinates></Point>
                        </Placemark>
                      </Folder>
                    </Folder>
                  </Document>
                </kml>
                """;

        KmzConversionResult result = converter.convert(createKmz(kml, "doc.kml"));

        assertThat(result.pointPlacemarks()).isEqualTo(3);
        assertThat(result.duplicatesRemoved())
                .as("separator noise must not defeat deduplication: 'KS 67 S1' is 'KS67_S1'")
                .isEqualTo(2);
        assertThat(result.importedFeatures()).isEqualTo(1);
    }

    @Test
    void reportsGeometriesItImported() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>KS67_S1</name>
                      <Point><coordinates>77.1234,28.5678</coordinates></Point>
                    </Placemark>
                    <Placemark>
                      <name>HT LINE</name>
                      <LineString><coordinates>77.1,28.5 77.2,28.6</coordinates></LineString>
                    </Placemark>
                    <Placemark>
                      <name>Penna River</name>
                      <Polygon><outerBoundaryIs><LinearRing>
                        <coordinates>77.1,28.5 77.2,28.5 77.2,28.6 77.1,28.5</coordinates>
                      </LinearRing></outerBoundaryIs></Polygon>
                    </Placemark>
                  </Document>
                </kml>
                """;

        KmzConversionResult result = converter.convert(createKmz(kml, "doc.kml"));

        assertThat(result.totalPlacemarks()).isEqualTo(3);
        assertThat(result.importedFeatures()).isEqualTo(3);
        assertThat(result.pointPlacemarks()).isEqualTo(1);
        assertThat(result.linePlacemarks()).isEqualTo(1);
        assertThat(result.polygonPlacemarks()).isEqualTo(1);
    }

    @Test
    void importsAllSupportedGeometries() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>Access Road</name>
                      <LineString>
                        <coordinates>77.10,28.50 77.11,28.51</coordinates>
                      </LineString>
                    </Placemark>
                    <Placemark>
                      <name>WTG-001</name>
                      <Point>
                        <coordinates>77.2302,28.6301</coordinates>
                      </Point>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "doc.kml");

        Map<String, Object> result = converter.convertToFeatureCollection(kmzBytes);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(2);
    }

    @Test
    void supportsRawKmlWithoutZipWrapper() {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>WTG-RAW</name>
                      <Point>
                        <coordinates>77.3000,28.7000</coordinates>
                      </Point>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] rawKmlBytes = kml.getBytes(StandardCharsets.UTF_8);

        Map<String, Object> result = converter.convertToFeatureCollection(rawKmlBytes);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> features = (List<Map<String, Object>>) result.get("features");
        assertThat(features).hasSize(1);

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) features.get(0).get("properties");
        assertThat(properties).containsEntry("externalId", "WTG-RAW");
    }

    @Test
    void throwsExceptionOnCorruptBytes() {
        byte[] corruptBytes = new byte[]{0, 1, 2, 3, 4, 5, 6, 7};

        assertThatThrownBy(() -> converter.convertToFeatureCollection(corruptBytes))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Failed to parse KML XML");
    }

    @Test
    void throwsExceptionWhenZeroPlacemarksFound() throws Exception {
        String kml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <name>Empty Doc</name>
                  </Document>
                </kml>
                """;
        byte[] kmzBytes = createKmz(kml, "doc.kml");

        assertThatThrownBy(() -> converter.convertToFeatureCollection(kmzBytes))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("KMZ file contains no valid Point placemarks");
    }

    @Test
    void rejectsExternalDoctypeEntityXxe() {
        String xxeKml = """
                <?xml version="1.0" encoding="UTF-8"?>
                <!DOCTYPE kml [
                  <!ENTITY xxe SYSTEM "file:///etc/passwd">
                ]>
                <kml xmlns="http://www.opengis.net/kml/2.2">
                  <Document>
                    <Placemark>
                      <name>&xxe;</name>
                      <Point>
                        <coordinates>77.23,28.63</coordinates>
                      </Point>
                    </Placemark>
                  </Document>
                </kml>
                """;
        byte[] rawBytes = xxeKml.getBytes(StandardCharsets.UTF_8);

        assertThatThrownBy(() -> converter.convertToFeatureCollection(rawBytes))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Failed to parse KML XML");
    }
}

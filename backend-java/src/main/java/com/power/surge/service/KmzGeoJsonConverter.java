package com.power.surge.service;

import org.springframework.stereotype.Component;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Component
public class KmzGeoJsonConverter {

    private static final byte[] ZIP_MAGIC = new byte[]{0x50, 0x4B, 0x03, 0x04};

    /**
     * Separator used to join KML folder names into {@code kmlFolderPath}. Deliberately padded with
     * spaces so a bare slash inside a folder name (e.g. "220/11KV") is not read as a separator.
     */
    public static final String FOLDER_PATH_SEPARATOR = " / ";

    public Map<String, Object> convertToFeatureCollection(byte[] fileBytes) {
        return convert(fileBytes).featureCollection();
    }

    /**
     * Converts a KMZ/KML archive into a Point FeatureCollection, annotating every feature with the
     * KML folder it was found in and discarding duplicates.
     *
     * <p>Survey exports routinely nest a copy of the entire tree under one of their own folders —
     * the reference Uravakonda file contains 903 Point placemarks describing only 303 distinct
     * assets. Without deduplication each asset is persisted three times under suffixed IDs.</p>
     */
    public KmzConversionResult convert(byte[] fileBytes) {
        if (fileBytes == null || fileBytes.length == 0) {
            throw new IllegalArgumentException("File content must not be empty");
        }

        byte[] kmlBytes = isZipArchive(fileBytes) ? extractKmlFromKmz(fileBytes) : fileBytes;
        Document document = parseXml(kmlBytes);

        ExtractionContext context = new ExtractionContext();
        walk(document.getDocumentElement(), new ArrayDeque<>(), context);

        if (context.features.isEmpty()) {
            throw new IllegalArgumentException("KMZ file contains no valid Point placemarks");
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", context.features);

        return new KmzConversionResult(
                featureCollection,
                context.totalPlacemarks,
                context.pointPlacemarks,
                context.linePlacemarks,
                context.polygonPlacemarks,
                context.duplicatesRemoved,
                Map.copyOf(context.skippedByGeometry)
        );
    }

    private static final class ExtractionContext {
        private final List<Map<String, Object>> features = new ArrayList<>();
        private final Set<String> seenKeys = new HashSet<>();
        private final Map<String, Integer> skippedByGeometry = new LinkedHashMap<>();
        private int totalPlacemarks;
        private int pointPlacemarks;
        private int linePlacemarks;
        private int polygonPlacemarks;
        private int duplicatesRemoved;
    }

    /**
     * Depth-first walk that keeps the enclosing Folder/Document names on a stack, so each Placemark
     * can be tagged with its full folder path. The flat {@code getElementsByTagName("Placemark")}
     * approach this replaces discarded that context entirely.
     */
    private void walk(Element element, Deque<String> folderPath, ExtractionContext context) {
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }
            Element child = (Element) node;
            String localName = localName(child);

            if ("Folder".equals(localName) || "Document".equals(localName)) {
                String name = directChildText(child, "name");
                boolean pushed = false;
                if (name != null && !name.isBlank()) {
                    folderPath.addLast(name.trim());
                    pushed = true;
                }
                walk(child, folderPath, context);
                if (pushed) {
                    folderPath.removeLast();
                }
            } else if ("Placemark".equals(localName)) {
                handlePlacemark(child, folderPath, context);
            } else {
                walk(child, folderPath, context);
            }
        }
    }

    private void handlePlacemark(Element placemark, Deque<String> folderPath, ExtractionContext context) {
        context.totalPlacemarks++;

        Map<String, Object> geometry = extractGeometry(placemark, context);
        if (geometry == null) {
            return;
        }

        Map<String, Object> properties = new LinkedHashMap<>();

        Element nameElem = getFirstDescendantByLocalName(placemark, "name");
        String externalId = nameElem == null ? null : nameElem.getTextContent();
        if (externalId != null && !externalId.isBlank()) {
            externalId = externalId.trim();
            properties.put("externalId", externalId);
        } else {
            externalId = "";
        }

        if (!folderPath.isEmpty()) {
            properties.put("kmlFolder", folderPath.peekLast());
            properties.put("kmlFolderPath", String.join(FOLDER_PATH_SEPARATOR, folderPath));
        }

        extractExtendedData(placemark, properties);

        // Deduplicate on identity + geometry. Separator noise in the name is collapsed so that
        // "KS-38_S3" and "KS 38 S3" at the same position are recognised as one asset. Lines and
        // polygons key on their full coordinate list, since survey files repeat whole folder trees
        // and "Path Measure" appears dozens of times with different geometry each time.
        String dedupeKey = externalId.toUpperCase(Locale.ROOT).replaceAll("[\\s_\\-.]", "")
                + "@" + geometry.get("type") + ":" + geometryFingerprint(geometry);
        if (!context.seenKeys.add(dedupeKey)) {
            context.duplicatesRemoved++;
            return;
        }

        Map<String, Object> feature = new LinkedHashMap<>();
        feature.put("type", "Feature");
        feature.put("geometry", geometry);
        feature.put("properties", properties);

        context.features.add(feature);
    }

    /**
     * Builds the GeoJSON geometry for a placemark, counting it by type.
     *
     * <p>Point, LineString and Polygon are all imported. Earlier revisions kept only Points and
     * silently discarded the rest, which in the reference file threw away every road, HT line,
     * river and land boundary — 161 placemarks.</p>
     */
    private Map<String, Object> extractGeometry(Element placemark, ExtractionContext context) {
        Element point = getFirstDescendantByLocalName(placemark, "Point");
        if (point != null) {
            double[] lonLat = firstCoordinate(point);
            if (lonLat == null) {
                return null;
            }
            context.pointPlacemarks++;
            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(lonLat[0], lonLat[1]));
            return geometry;
        }

        Element line = getFirstDescendantByLocalName(placemark, "LineString");
        if (line != null) {
            List<List<Double>> coordinates = parseCoordinateList(line);
            if (coordinates.size() < 2) {
                context.skippedByGeometry.merge("LineString", 1, Integer::sum);
                return null;
            }
            context.linePlacemarks++;
            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "LineString");
            geometry.put("coordinates", coordinates);
            return geometry;
        }

        Element polygon = getFirstDescendantByLocalName(placemark, "Polygon");
        if (polygon != null) {
            Element outer = getFirstDescendantByLocalName(polygon, "outerBoundaryIs");
            List<List<Double>> ring = parseCoordinateList(outer != null ? outer : polygon);
            if (ring.size() < 4) {
                context.skippedByGeometry.merge("Polygon", 1, Integer::sum);
                return null;
            }
            // GeoJSON requires a closed ring; KML frequently omits the repeated last vertex.
            if (!ring.get(0).equals(ring.get(ring.size() - 1))) {
                ring.add(ring.get(0));
            }
            context.polygonPlacemarks++;
            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Polygon");
            geometry.put("coordinates", List.of(ring));
            return geometry;
        }

        context.skippedByGeometry.merge(detectGeometryType(placemark), 1, Integer::sum);
        return null;
    }

    private double[] firstCoordinate(Element geometryElement) {
        Element coordElem = getFirstDescendantByLocalName(geometryElement, "coordinates");
        return coordElem == null ? null : parseCoordinates(coordElem.getTextContent());
    }

    private List<List<Double>> parseCoordinateList(Element geometryElement) {
        List<List<Double>> coordinates = new ArrayList<>();
        Element coordElem = getFirstDescendantByLocalName(geometryElement, "coordinates");
        if (coordElem == null || coordElem.getTextContent() == null) {
            return coordinates;
        }
        for (String token : coordElem.getTextContent().trim().split("\\s+")) {
            if (token.isBlank()) {
                continue;
            }
            String[] parts = token.split(",");
            if (parts.length < 2) {
                continue;
            }
            try {
                coordinates.add(List.of(
                        Double.parseDouble(parts[0].trim()),
                        Double.parseDouble(parts[1].trim())));
            } catch (NumberFormatException ignored) {
                // A malformed vertex drops out rather than failing the whole import.
            }
        }
        return coordinates;
    }

    /** Cheap positional identity: vertex count plus the first and last vertex. */
    private String geometryFingerprint(Map<String, Object> geometry) {
        Object coordinates = geometry.get("coordinates");
        if ("Point".equals(geometry.get("type"))) {
            @SuppressWarnings("unchecked")
            List<Double> point = (List<Double>) coordinates;
            return String.format(Locale.ROOT, "%.7f,%.7f", point.get(0), point.get(1));
        }
        List<?> vertices = "Polygon".equals(geometry.get("type"))
                ? (List<?>) ((List<?>) coordinates).get(0)
                : (List<?>) coordinates;
        @SuppressWarnings("unchecked")
        List<Double> first = (List<Double>) vertices.get(0);
        @SuppressWarnings("unchecked")
        List<Double> last = (List<Double>) vertices.get(vertices.size() - 1);
        return String.format(Locale.ROOT, "%d/%.7f,%.7f/%.7f,%.7f",
                vertices.size(), first.get(0), first.get(1), last.get(0), last.get(1));
    }

    private String detectGeometryType(Element placemark) {
        for (String type : List.of("MultiGeometry", "LinearRing", "Model", "Track")) {
            if (getFirstDescendantByLocalName(placemark, type) != null) {
                return type;
            }
        }
        return "None";
    }

    private String directChildText(Element parent, String localName) {
        NodeList children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE && localName.equals(localName((Element) node))) {
                return node.getTextContent();
            }
        }
        return null;
    }

    private static String localName(Element element) {
        return element.getLocalName() != null ? element.getLocalName() : element.getTagName();
    }

    private boolean isZipArchive(byte[] bytes) {
        if (bytes.length < 4) {
            return false;
        }
        return bytes[0] == ZIP_MAGIC[0]
                && bytes[1] == ZIP_MAGIC[1]
                && bytes[2] == ZIP_MAGIC[2]
                && bytes[3] == ZIP_MAGIC[3];
    }

    private byte[] extractKmlFromKmz(byte[] zipBytes) {
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zipBytes))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                if (!entry.isDirectory() && entry.getName().toLowerCase().endsWith(".kml")) {
                    return zis.readAllBytes();
                }
            }
            throw new IllegalArgumentException("KMZ archive does not contain a .kml file");
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to read KMZ archive: " + e.getMessage(), e);
        }
    }

    private Document parseXml(byte[] xmlBytes) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);

            DocumentBuilder builder = factory.newDocumentBuilder();
            try (InputStream is = new ByteArrayInputStream(xmlBytes)) {
                return builder.parse(is);
            }
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to parse KML XML: " + e.getMessage(), e);
        }
    }

    private double[] parseCoordinates(String coordText) {
        if (coordText == null || coordText.isBlank()) {
            return null;
        }
        String trimmed = coordText.trim();
        String normalized = trimmed.replaceAll("\\s*,\\s*", ",");
        String[] tokens = normalized.split("\\s+");
        if (tokens.length == 0 || tokens[0].isBlank()) {
            return null;
        }
        String firstPair = tokens[0];
        String[] parts = firstPair.split(",");
        if (parts.length < 2) {
            return null;
        }
        try {
            double lon = Double.parseDouble(parts[0].trim());
            double lat = Double.parseDouble(parts[1].trim());
            return new double[]{lon, lat};
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private void extractExtendedData(Element placemark, Map<String, Object> properties) {
        Element extendedData = getFirstDescendantByLocalName(placemark, "ExtendedData");
        if (extendedData == null) {
            return;
        }

        // Style 1: <Data name="..."> <value>...</value> </Data>
        NodeList dataList = extendedData.getElementsByTagNameNS("*", "Data");
        for (int i = 0; i < dataList.getLength(); i++) {
            Node node = dataList.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element dataElem = (Element) node;
                String nameAttr = dataElem.getAttribute("name");
                if (nameAttr != null && !nameAttr.isBlank()) {
                    Element valElem = getFirstDescendantByLocalName(dataElem, "value");
                    if (valElem != null) {
                        properties.put(nameAttr.trim(), valElem.getTextContent().trim());
                    }
                }
            }
        }

        // Style 2: <SchemaData> <SimpleData name="...">...</SimpleData> </SchemaData>
        NodeList simpleDataList = extendedData.getElementsByTagNameNS("*", "SimpleData");
        for (int i = 0; i < simpleDataList.getLength(); i++) {
            Node node = simpleDataList.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element simpleDataElem = (Element) node;
                String nameAttr = simpleDataElem.getAttribute("name");
                if (nameAttr != null && !nameAttr.isBlank()) {
                    properties.put(nameAttr.trim(), simpleDataElem.getTextContent().trim());
                }
            }
        }
    }

    private Element getFirstDescendantByLocalName(Element parent, String localName) {
        NodeList nodeList = parent.getElementsByTagNameNS("*", localName);
        if (nodeList.getLength() > 0) {
            return (Element) nodeList.item(0);
        }
        return null;
    }
}

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

/** Audit log timestamp: Seoul local time with offset, second precision (e.g. 2026-10-21T08:59:59+09:00). */
public class LogTimestamp {
    private static final DateTimeFormatter FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX");
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");

    public static String toIso(long epochMillis) {
        return Instant.ofEpochMilli(epochMillis).atZone(SEOUL).format(FORMAT);
    }
}

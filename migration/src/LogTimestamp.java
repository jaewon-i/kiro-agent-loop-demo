import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

/** Audit log timestamp: Seoul local time with offset, second precision (e.g. 2026-10-21T08:59:59+09:00). */
public class LogTimestamp {
    public static String toIso(long epochMillis) {
        ZonedDateTime zdt = Instant.ofEpochMilli(epochMillis)
                .atZone(ZoneId.of("Asia/Seoul"))
                .truncatedTo(ChronoUnit.SECONDS);
        return zdt.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }
}

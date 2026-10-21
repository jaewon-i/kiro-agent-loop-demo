import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

/** Invoice issue date, shown as the Seoul calendar date (e.g. 2026-10-21). */
public class InvoiceFormatter {
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");

    public static String issueDate(long epochMillis) {
        return Instant.ofEpochMilli(epochMillis).atZone(SEOUL).toLocalDate().format(DateTimeFormatter.ISO_LOCAL_DATE);
    }
}

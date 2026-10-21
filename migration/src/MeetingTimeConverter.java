import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;

/** Converts a meeting time "yyyy-MM-dd HH:mm" from one time zone to another (DST aware). */
public class MeetingTimeConverter {
    private static final DateTimeFormatter FORMAT =
            DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm").withResolverStyle(ResolverStyle.STRICT);

    public static String convert(String dateTime, String fromZone, String toZone) {
        try {
            LocalDateTime local = LocalDateTime.parse(dateTime, FORMAT);
            ZonedDateTime from = local.atZone(ZoneId.of(fromZone));
            ZonedDateTime to = from.withZoneSameInstant(ZoneId.of(toZone));
            return to.format(FORMAT);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("invalid date-time: " + dateTime);
        }
    }
}

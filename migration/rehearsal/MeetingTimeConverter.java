import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;

/** Converts a meeting time "yyyy-MM-dd HH:mm" from one time zone to another (DST aware). */
public class MeetingTimeConverter {
    private static final DateTimeFormatter FORMAT = DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm").withResolverStyle(ResolverStyle.STRICT);

    public static String convert(String dateTime, String fromZone, String toZone) {
        try {
            return LocalDateTime.parse(dateTime, FORMAT).atZone(ZoneId.of(fromZone))
                    .withZoneSameInstant(ZoneId.of(toZone)).format(FORMAT);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("invalid date-time: " + dateTime);
        }
    }
}

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;

/** Converts a meeting time "yyyy-MM-dd HH:mm" from one time zone to another (DST aware). */
public class MeetingTimeConverter {
    public static String convert(String dateTime, String fromZone, String toZone) {
        SimpleDateFormat in = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        in.setLenient(false);
        in.setTimeZone(TimeZone.getTimeZone(fromZone));
        SimpleDateFormat out = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        out.setTimeZone(TimeZone.getTimeZone(toZone));
        try {
            Date instant = in.parse(dateTime);
            return out.format(instant);
        } catch (ParseException e) {
            throw new IllegalArgumentException("invalid date-time: " + dateTime);
        }
    }
}

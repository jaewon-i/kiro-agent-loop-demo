import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;

/** Audit log timestamp: Seoul local time with offset, second precision (e.g. 2026-10-21T08:59:59+09:00). */
public class LogTimestamp {
    public static String toIso(long epochMillis) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX");
        format.setTimeZone(TimeZone.getTimeZone("Asia/Seoul"));
        return format.format(new Date(epochMillis));
    }
}

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;

/** Invoice issue date, shown as the Seoul calendar date (e.g. 2026-10-21). */
public class InvoiceFormatter {
    public static String issueDate(long epochMillis) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd");
        format.setTimeZone(TimeZone.getTimeZone("Asia/Seoul"));
        return format.format(new Date(epochMillis));
    }
}

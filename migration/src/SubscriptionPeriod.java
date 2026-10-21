import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.TimeZone;

/** Subscription end date = start + N months (clamped to month end, e.g. Jan 31 + 1 month = Feb 28). */
public class SubscriptionPeriod {
    public static String endDate(String startDate, int months) {
        if (months <= 0) throw new IllegalArgumentException("months must be > 0");
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd");
        format.setLenient(false);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        try {
            calendar.setTime(format.parse(startDate));
        } catch (ParseException e) {
            throw new IllegalArgumentException("invalid date: " + startDate);
        }
        calendar.add(Calendar.MONTH, months);
        return format.format(calendar.getTime());
    }
}

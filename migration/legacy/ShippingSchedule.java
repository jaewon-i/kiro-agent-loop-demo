import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.TimeZone;

/** Delivery date = order date + N business days (Saturday/Sunday skipped). */
public class ShippingSchedule {
    public static String deliveryDate(String orderDate, int businessDays) {
        if (businessDays < 0) throw new IllegalArgumentException("businessDays must be >= 0");
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd");
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        format.setLenient(false);
        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        try {
            calendar.setTime(format.parse(orderDate));
        } catch (ParseException e) {
            throw new IllegalArgumentException("invalid date: " + orderDate);
        }
        int added = 0;
        while (added < businessDays) {
            calendar.add(Calendar.DAY_OF_MONTH, 1);
            int day = calendar.get(Calendar.DAY_OF_WEEK);
            if (day != Calendar.SATURDAY && day != Calendar.SUNDAY) added++;
        }
        return format.format(calendar.getTime());
    }
}

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;

/** Delivery date = order date + N business days (Saturday/Sunday skipped). */
public class ShippingSchedule {
    private static final DateTimeFormatter FORMAT = DateTimeFormatter.ofPattern("uuuu-MM-dd").withResolverStyle(ResolverStyle.STRICT);

    public static String deliveryDate(String orderDate, int businessDays) {
        if (businessDays < 0) throw new IllegalArgumentException("businessDays must be >= 0");
        LocalDate date;
        try {
            date = LocalDate.parse(orderDate, FORMAT);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("invalid date: " + orderDate);
        }
        int added = 0;
        while (added < businessDays) {
            date = date.plusDays(1);
            if (date.getDayOfWeek() != DayOfWeek.SATURDAY && date.getDayOfWeek() != DayOfWeek.SUNDAY) added++;
        }
        return date.format(FORMAT);
    }
}

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;

/** Subscription end date = start + N months (clamped to month end, e.g. Jan 31 + 1 month = Feb 28). */
public class SubscriptionPeriod {
    public static String endDate(String startDate, int months) {
        if (months <= 0) throw new IllegalArgumentException("months must be > 0");
        DateTimeFormatter format = DateTimeFormatter.ofPattern("uuuu-MM-dd")
                .withResolverStyle(ResolverStyle.STRICT);
        LocalDate date;
        try {
            date = LocalDate.parse(startDate, format);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("invalid date: " + startDate);
        }
        return date.plusMonths(months).format(format);
    }
}

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;

/** Age in full years on a given date. Birthday not yet reached this year => one year less. */
public class AgeCalculator {
    public static int age(String birthDate, String onDate) {
        LocalDate birth = parse(birthDate);
        LocalDate on = parse(onDate);
        if (on.isBefore(birth)) throw new IllegalArgumentException("onDate before birthDate");
        int years = on.getYear() - birth.getYear();
        int onMonth = on.getMonthValue(), birthMonth = birth.getMonthValue();
        if (onMonth < birthMonth
                || (onMonth == birthMonth && on.getDayOfMonth() < birth.getDayOfMonth())) {
            years--;
        }
        return years;
    }

    private static final DateTimeFormatter FORMAT =
            DateTimeFormatter.ofPattern("uuuu-MM-dd").withResolverStyle(ResolverStyle.STRICT);

    private static LocalDate parse(String text) {
        try {
            return LocalDate.parse(text, FORMAT);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("invalid date: " + text);
        }
    }
}

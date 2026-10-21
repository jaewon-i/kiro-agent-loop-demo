import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.TimeZone;

/** Age in full years on a given date. Birthday not yet reached this year => one year less. */
public class AgeCalculator {
    public static int age(String birthDate, String onDate) {
        Calendar birth = parse(birthDate);
        Calendar on = parse(onDate);
        if (on.before(birth)) throw new IllegalArgumentException("onDate before birthDate");
        int years = on.get(Calendar.YEAR) - birth.get(Calendar.YEAR);
        int onMonth = on.get(Calendar.MONTH), birthMonth = birth.get(Calendar.MONTH);
        if (onMonth < birthMonth
                || (onMonth == birthMonth && on.get(Calendar.DAY_OF_MONTH) < birth.get(Calendar.DAY_OF_MONTH))) {
            years--;
        }
        return years;
    }

    private static Calendar parse(String text) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd");
        format.setLenient(false);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        try {
            calendar.setTime(format.parse(text));
        } catch (ParseException e) {
            throw new IllegalArgumentException("invalid date: " + text);
        }
        return calendar;
    }
}

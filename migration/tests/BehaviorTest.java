import java.util.ArrayList;
import java.util.List;

/**
 * Behavior tests for the date/time classes. They pin the CURRENT behavior so that the
 * java.util.Date -> java.time migration must not change any result. Agents must not edit this file.
 */
public class BehaviorTest {
    private static final List<String> failures = new ArrayList<>();
    private static int checks = 0;

    interface Check {
        void run() throws Exception;
        interface Value { Object get() throws Exception; }
    }

    private static void eq(String cls, String what, Object expected, Check.Value actual) {
        checks++;
        try {
            Object got = actual.get();
            if (!expected.equals(got)) failures.add(cls + ": " + what + " expected=" + expected + " actual=" + got);
        } catch (Exception e) {
            failures.add(cls + ": " + what + " threw " + e);
        }
    }

    private static void throwsIAE(String cls, String what, Check c) {
        checks++;
        try {
            c.run();
            failures.add(cls + ": " + what + " expected IllegalArgumentException, nothing thrown");
        } catch (IllegalArgumentException expected) {
            // ok
        } catch (Exception e) {
            failures.add(cls + ": " + what + " expected IllegalArgumentException, got " + e);
        }
    }

    public static void main(String[] args) {
        // InvoiceFormatter — Seoul calendar date (UTC+9)
        eq("InvoiceFormatter", "2026-10-20T23:59:59Z", "2026-10-21", () -> InvoiceFormatter.issueDate(1792540799000L));
        eq("InvoiceFormatter", "2026-10-21T14:59Z", "2026-10-21", () -> InvoiceFormatter.issueDate(1792594740000L));
        eq("InvoiceFormatter", "2026-10-21T15:00Z", "2026-10-22", () -> InvoiceFormatter.issueDate(1792594800000L));

        // LogTimestamp — Seoul offset, second precision (milliseconds are dropped)
        eq("LogTimestamp", "whole second", "2026-10-21T08:59:59+09:00", () -> LogTimestamp.toIso(1792540799000L));
        eq("LogTimestamp", "millis dropped", "2026-10-21T08:59:59+09:00", () -> LogTimestamp.toIso(1792540799123L));
        eq("LogTimestamp", "midnight", "2026-10-22T00:00:00+09:00", () -> LogTimestamp.toIso(1792594800000L));

        // ShippingSchedule — business days, strict parsing
        eq("ShippingSchedule", "Wed +2", "2026-10-23", () -> ShippingSchedule.deliveryDate("2026-10-21", 2));
        eq("ShippingSchedule", "Fri +1 skips weekend", "2026-10-26", () -> ShippingSchedule.deliveryDate("2026-10-23", 1));
        eq("ShippingSchedule", "+0 same day", "2026-10-23", () -> ShippingSchedule.deliveryDate("2026-10-23", 0));
        eq("ShippingSchedule", "year boundary", "2027-01-04", () -> ShippingSchedule.deliveryDate("2026-12-31", 2));
        throwsIAE("ShippingSchedule", "Feb 30 rejected", () -> ShippingSchedule.deliveryDate("2026-02-30", 1));
        throwsIAE("ShippingSchedule", "negative days", () -> ShippingSchedule.deliveryDate("2026-10-21", -1));

        // MeetingTimeConverter — zones and DST (New York DST starts 2026-03-08 07:00Z)
        eq("MeetingTimeConverter", "Seoul -> UTC", "2026-10-21 00:00",
                () -> MeetingTimeConverter.convert("2026-10-21 09:00", "Asia/Seoul", "UTC"));
        eq("MeetingTimeConverter", "Seoul -> UTC crosses year", "2025-12-31 23:30",
                () -> MeetingTimeConverter.convert("2026-01-01 08:30", "Asia/Seoul", "UTC"));
        eq("MeetingTimeConverter", "before DST", "2026-03-08 01:59",
                () -> MeetingTimeConverter.convert("2026-03-08 06:59", "UTC", "America/New_York"));
        eq("MeetingTimeConverter", "after DST", "2026-03-08 03:00",
                () -> MeetingTimeConverter.convert("2026-03-08 07:00", "UTC", "America/New_York"));
        throwsIAE("MeetingTimeConverter", "bad format", () -> MeetingTimeConverter.convert("2026/10/21 9:00", "UTC", "UTC"));

        // AgeCalculator — full years, leap-day birthday
        eq("AgeCalculator", "day before birthday", 25, () -> AgeCalculator.age("2000-10-22", "2026-10-21"));
        eq("AgeCalculator", "on birthday", 26, () -> AgeCalculator.age("2000-10-21", "2026-10-21"));
        eq("AgeCalculator", "leap-day born, Feb 28", 25, () -> AgeCalculator.age("2000-02-29", "2026-02-28"));
        eq("AgeCalculator", "leap-day born, Mar 1", 26, () -> AgeCalculator.age("2000-02-29", "2026-03-01"));
        throwsIAE("AgeCalculator", "future birth", () -> AgeCalculator.age("2030-01-01", "2026-10-21"));
        throwsIAE("AgeCalculator", "bad date", () -> AgeCalculator.age("2000-13-01", "2026-10-21"));

        // SubscriptionPeriod — month arithmetic clamps to month end
        eq("SubscriptionPeriod", "Jan 31 + 1", "2026-02-28", () -> SubscriptionPeriod.endDate("2026-01-31", 1));
        eq("SubscriptionPeriod", "leap year Jan 31 + 1", "2024-02-29", () -> SubscriptionPeriod.endDate("2024-01-31", 1));
        eq("SubscriptionPeriod", "+12 months", "2027-10-21", () -> SubscriptionPeriod.endDate("2026-10-21", 12));
        throwsIAE("SubscriptionPeriod", "zero months", () -> SubscriptionPeriod.endDate("2026-10-21", 0));
        throwsIAE("SubscriptionPeriod", "bad date", () -> SubscriptionPeriod.endDate("2026-02-30", 1));

        if (failures.isEmpty()) {
            System.out.println("ALL " + checks + " BEHAVIOR CHECKS PASSED");
        } else {
            System.out.println(failures.size() + " of " + checks + " behavior checks FAILED:");
            for (String f : failures) System.out.println("  - " + f);
            System.exit(1);
        }
    }
}

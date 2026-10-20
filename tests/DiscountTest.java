public class DiscountTest {
    private static void eq(int expected, int actual) {
        if (expected != actual) throw new AssertionError("expected=" + expected + " actual=" + actual);
    }
    private static void invalid(int price, int rate) {
        try {
            DiscountCalculator.discount(price, rate);
            throw new AssertionError("Expected IllegalArgumentException for rate=" + rate);
        } catch (IllegalArgumentException expected) { }
    }
    public static void main(String[] args) {
        eq(900, DiscountCalculator.discount(1000, 10));
        eq(1000, DiscountCalculator.discount(1000, 0));
        eq(0, DiscountCalculator.discount(1000, 100));
        invalid(1000, -1);
        invalid(1000, 101);
        System.out.println("ALL TESTS PASSED");
    }
}

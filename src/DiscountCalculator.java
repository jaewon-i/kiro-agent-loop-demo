public class DiscountCalculator {
    public static int discount(int price, int rate) {
        // BUG: negative rates and rates >100 are accepted.
        return price - (price * rate / 100);
    }
}

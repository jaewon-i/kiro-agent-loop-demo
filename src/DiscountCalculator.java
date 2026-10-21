public class DiscountCalculator {
    public static int discount(int price, int rate) {
        if (price < 0) throw new IllegalArgumentException("invalid price");
        if (rate < 0 || rate > 100) throw new IllegalArgumentException("invalid rate");
        return price - (price * rate / 100);
    }
}

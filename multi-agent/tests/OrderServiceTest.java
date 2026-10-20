import java.util.concurrent.*;
import java.util.*;

/** Deterministic Java acceptance gate; agents must not edit this file. */
public class OrderServiceTest {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static void invalid(Runnable r) {
        try { r.run(); throw new AssertionError("Expected IllegalArgumentException"); }
        catch (IllegalArgumentException expected) { }
    }
    public static void main(String[] args) throws Exception {
        OrderService s = new OrderService();
        var first = s.create("req-1", "book", 2, 100);
        check(first.total() == 200L, "total");
        check(s.create("req-1", "book", 2, 100) == first, "idempotent replay must return same order");
        invalid(() -> s.create("", "book", 1, 100));
        invalid(() -> s.create("req-2", "", 1, 100));
        invalid(() -> s.create("req-3", "book", 0, 100));
        invalid(() -> s.create("req-4", "book", 1, -1));
        // The same idempotency key with a different payload must not silently succeed.
        invalid(() -> s.create("req-1", "different", 2, 100));
        check(s.create("large", "book", 100000, 100000).total() == 10000000000L, "overflow");
        System.out.println("ALL ORDER ACCEPTANCE TESTS PASSED");
    }
}

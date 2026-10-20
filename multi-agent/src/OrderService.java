import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/** Intentionally flawed starter for the AI Developer / QA feedback demo. */
public final class OrderService {
    private final ConcurrentMap<String, Order> orders = new ConcurrentHashMap<>();

    public Order create(String requestId, String itemId, int quantity, int unitPrice) {
        if (requestId == null || requestId.isBlank()) throw new IllegalArgumentException("requestId required");
        if (itemId == null || itemId.isBlank()) throw new IllegalArgumentException("itemId required");
        if (quantity <= 0 || unitPrice < 0) throw new IllegalArgumentException("invalid amount");
        // BUG: check-then-act is not atomic under concurrent requests.
        Order existing = orders.get(requestId);
        if (existing != null) return existing;
        Order created = new Order(requestId, itemId, quantity, unitPrice);
        orders.put(requestId, created);
        return created;
    }

    public int count() { return orders.size(); }

    public record Order(String requestId, String itemId, int quantity, int unitPrice) {
        public long total() { return (long) quantity * unitPrice; }
    }
}

package io.packetcraft.ptmp;

import com.cisco.pt.impl.OptionsManager;
import com.cisco.pt.ipc.IPCFactory;
import com.cisco.pt.ipc.IPCError;
import com.cisco.pt.ipc.enums.DeviceType;
import com.cisco.pt.ipc.sim.Device;
import com.cisco.pt.ipc.sim.Network;
import com.cisco.pt.ipc.ui.IPC;
import com.cisco.pt.ptmp.ConnectionNegotiationProperties;
import com.cisco.pt.ptmp.PacketTracerSession;
import com.cisco.pt.ptmp.PacketTracerSessionFactory;
import com.cisco.pt.ptmp.impl.PacketTracerSessionFactoryImpl;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Locale;

/**
 * PacketCraft's narrow native Packet Tracer adapter.
 *
 * Protocol: one tab-separated command per stdin line, one JSON object per stdout
 * line. It intentionally has no arbitrary IPC or JavaScript execution command.
 * The Cisco IPC framework is supplied by the user's Packet Tracer installation
 * and is never copied into this repository.
 */
public final class PacketCraftPtmp {
    private PacketTracerSession session;
    private IPC ipc;

    public static void main(String[] arguments) throws Exception {
        new PacketCraftPtmp().run();
    }

    private void run() throws Exception {
        try (BufferedReader input = new BufferedReader(new InputStreamReader(System.in, "UTF-8"))) {
            String line;
            while ((line = input.readLine()) != null) {
                if ("QUIT".equals(line)) {
                    disconnect();
                    reply("{\"ok\":true,\"event\":\"closed\"}");
                    return;
                }
                try {
                    String[] parts = line.split("\\t", -1);
                    if ("STATUS".equals(parts[0])) {
                        connect();
                        reply("{\"ok\":true,\"connected\":true}");
                    } else if ("TOPOLOGY".equals(parts[0])) {
                        connect();
                        reply(topology());
                    } else if ("ADD_DEVICE".equals(parts[0]) && parts.length == 5) {
                        connect();
                        reply(addDevice(parts[1], parts[2], parts[3], parts[4]));
                    } else {
                        reply(error("unsupported or malformed command"));
                    }
                } catch (IPCError exception) {
                    reply(error(exception.getMessage()));
                } catch (Exception exception) {
                    reply(error(exception.getMessage()));
                }
            }
        } finally {
            disconnect();
        }
    }

    private void connect() {
        if (ipc != null) return;
        String application = requiredEnvironment("PACKETCRAFT_PTMP_APPLICATION");
        String secret = requiredEnvironment("PACKETCRAFT_PTMP_SECRET");
        String host = environment("PACKETCRAFT_PTMP_HOST", "127.0.0.1");
        int port = Integer.parseInt(environment("PACKETCRAFT_PTMP_PORT", "39000"));

        ConnectionNegotiationProperties options = OptionsManager.getInstance().getConnectOpts();
        options.setAuthenticationApplication(application);
        options.setAuthenticationSecret(secret);
        PacketTracerSessionFactory factory = PacketTracerSessionFactoryImpl.getInstance();
        try {
            session = factory.openSession(host, port, options);
            if (!session.isConnected()) throw new IllegalStateException("Packet Tracer rejected the credentials");
            ipc = new IPCFactory(session).getIPC();
        } catch (Exception exception) {
            disconnect();
            throw new IllegalStateException("Packet Tracer PTMP connection failed: " + safeMessage(exception));
        }
    }

    private String topology() {
        Network network = ipc.network();
        StringBuilder devices = new StringBuilder();
        devices.append("[");
        for (int index = 0; index < network.getDeviceCount(); index++) {
            if (index > 0) devices.append(',');
            Device device = network.getDeviceAt(index);
            devices.append("{\"name\":\"").append(escape(device.getName())).append("\",")
                    .append("\"type\":\"").append(escape(device.getType().name())).append("\",")
                    .append("\"model\":\"").append(escape(device.getModel())).append("\"}");
        }
        devices.append("]");
        return "{\"ok\":true,\"devices\":" + devices + ",\"link_count\":" + network.getLinkCount() + "}";
    }

    private String addDevice(String type, String model, String x, String y) {
        DeviceType deviceType = DeviceType.valueOf(type.toUpperCase(Locale.ROOT));
        String name = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace().addDevice(
                deviceType, model, Double.parseDouble(x), Double.parseDouble(y));
        if (name == null || name.isEmpty()) throw new IllegalStateException("Packet Tracer did not create the requested device");
        return "{\"ok\":true,\"name\":\"" + escape(name) + "\"}";
    }

    private void disconnect() {
        if (session != null) {
            try { session.close(); } catch (Exception ignored) { }
        }
        session = null;
        ipc = null;
    }

    private static String requiredEnvironment(String name) {
        String value = System.getenv(name);
        if (value == null || value.trim().isEmpty()) throw new IllegalStateException("missing environment setting: " + name);
        return value.trim();
    }

    private static String environment(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }

    private static String error(String message) {
        return "{\"ok\":false,\"error\":\"" + escape(message) + "\"}";
    }

    private static String escape(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r");
    }

    private static String safeMessage(Exception exception) {
        return exception.getMessage() == null ? exception.getClass().getSimpleName() : exception.getMessage();
    }

    private static void reply(String payload) {
        System.out.println(payload);
        System.out.flush();
    }
}

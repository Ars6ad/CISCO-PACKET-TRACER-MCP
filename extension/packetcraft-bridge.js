// PacketCraft Script Module bridge; generated locally. Do not edit MAILBOX.
// Uses typed JSON jobs only. It never evaluates job text as JavaScript.
var PACKETCRAFT_PROTOCOL = 1;
// getUserFolder() is Packet Tracer's documented OS-user folder. This makes a
// compiled .pts portable: no Windows username is baked into the extension.
var MAILBOX = String(ipc.appWindow().getUserFolder()).replace(/\\/g, '/') + '/PacketCraft/script-bridge';
var POLL_MS = 500;
var packetcraftTimer = null;

function packetcraftPath(part) { return MAILBOX + '/' + part; }
function packetcraftFiles() { return ipc.systemFileManager(); }
function packetcraftWorkspace() { return ipc.appWindow().getActiveWorkspace().getLogicalWorkspace(); }
function packetcraftWriteAtomic(path, text) {
  var files = packetcraftFiles();
  var temp = path + '.tmp';
  if (!files.writeTextToFile(temp, text)) throw new Error('unable to write ' + temp);
  if (!files.moveSrcFileToDestFile(temp, path, true)) throw new Error('unable to move ' + path);
}
function packetcraftHeartbeat() {
  packetcraftWriteAtomic(packetcraftPath('heartbeat.json'), JSON.stringify({protocol: PACKETCRAFT_PROTOCOL, at: new Date().getTime()}));
}
function packetcraftType(kind, model) {
  // PT's documented DeviceType enum, with model-specific values where the
  // broad category is not sufficient (for example multilayer switches).
  // Keep this in lockstep with packetcraft_mcp.catalog.  Values are verified
  // against the PT 9 Script Module DeviceType documentation.
  var models = {
    '1941': 0, '2901': 0, '2911': 0, 'ISR4321': 0, 'ISR4331': 0, 'Router-PT': 0,
    '2960-24TT': 1, '3560-24PS': 16, 'Switch-PT': 1,
    'PC-PT': 8, 'Laptop-PT': 17, 'Server-PT': 9, 'AccessPoint-PT': 7
  };
  var kinds = {router: 0, switch: 1, host: 8, server: 9, access_point: 7};
  if (models[model] !== undefined) return models[model];
  if (kinds[kind] === undefined) throw new Error('unsupported device kind');
  return kinds[kind];
}
function packetcraftCable(kind) {
  var cables = {copper_straight: 8100, copper_cross: 8101, fiber: 8103, serial: 8106, auto: 8107};
  if (cables[kind] === undefined) throw new Error('unsupported cable');
  return cables[kind];
}
function packetcraftTopology() {
  var network = ipc.network(), devices = [], i, device;
  for (i = 0; i < network.getDeviceCount(); i++) {
    device = network.getDeviceAt(i);
    devices.push({name: String(device.getName()), model: String(device.getModel()), ports: device.getPorts()});
  }
  return {devices: devices, device_count: devices.length, link_count: network.getLinkCount()};
}
function packetcraftAction(action) {
  var a = action.arguments, ws, device, created;
  if (action.type === 'ping') return {pong: true};
  if (action.type === 'query_topology') return packetcraftTopology();
  ws = packetcraftWorkspace();
  if (action.type === 'create_device') {
    if (ipc.network().getDevice(a.name)) throw new Error('device already exists: ' + a.name);
    created = String(ws.addDevice(packetcraftType(a.kind, a.model), a.model, a.x, a.y));
    device = ipc.network().getDevice(created); device.setName(a.name);
    return {created: a.name, packet_tracer_name: created};
  }
  if (action.type === 'delete_device') return {deleted: a.name, ok: ws.removeDevice(a.name)};
  if (action.type === 'rename_device') { ipc.network().getDevice(a.name).setName(a.new_name); return {renamed: a.name, new_name: a.new_name}; }
  if (action.type === 'move_device') { ipc.network().getDevice(a.name).moveToLocation(a.x, a.y); return {moved: a.name}; }
  if (action.type === 'connect_ports') return {connected: ws.createLink(a.a, a.a_port, a.b, a.b_port, packetcraftCable(a.cable))};
  if (action.type === 'disconnect_port') return {disconnected: ws.deleteLink(a.name, a.port)};
  throw new Error('unsupported action');
}
function packetcraftProcess(fileName) {
  var files = packetcraftFiles(), source = packetcraftPath('jobs/' + fileName), request, reply, i, one;
  try {
    request = JSON.parse(String(files.getFileContents(source)));
    if (request.protocol !== PACKETCRAFT_PROTOCOL || !request.job_id || !request.actions) throw new Error('invalid job envelope');
    reply = {protocol: PACKETCRAFT_PROTOCOL, job_id: request.job_id, status: 'succeeded', results: []};
    for (i = 0; i < request.actions.length; i++) {
      one = request.actions[i];
      reply.results.push({type: one.type, result: packetcraftAction(one)});
    }
  } catch (error) {
    reply = {protocol: PACKETCRAFT_PROTOCOL, job_id: request && request.job_id ? request.job_id : fileName.replace('.json', ''), status: 'failed', error: String(error)};
  }
  packetcraftWriteAtomic(packetcraftPath('results/' + reply.job_id + '.json'), JSON.stringify(reply));
  files.removeFile(source);
}
function packetcraftTick() {
  var files, names, i;
  try {
    packetcraftHeartbeat(); files = packetcraftFiles(); names = files.getFilesInDirectory(packetcraftPath('jobs'));
    for (i = 0; i < names.length; i++) if (/^[0-9a-f]{32}\.json$/.test(String(names[i]))) packetcraftProcess(String(names[i]));
  } catch (error) { dprint('PacketCraft bridge error: ' + String(error)); }
}
function main() { packetcraftTick(); packetcraftTimer = setInterval(packetcraftTick, POLL_MS); }
function cleanUp() { if (packetcraftTimer !== null) clearInterval(packetcraftTimer); }

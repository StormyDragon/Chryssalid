const {spawnSync} = require('child_process');
const ffi = require('ffi');
const fs = require('fs');

const ArrayType = require('ref-array');
const lib = ffi.Library('libc', {
    'execvp': ['int', ['string', ArrayType('string')]],
    'execvpe': ['int', ['string', ArrayType('string'), ArrayType('string')]],
    'fcntl': ['int', ['int', 'int', 'int']],
});

function execvpe(program, arguments, environment) {
    const arr = [
        program,
        ...arguments,
        null
    ];
    const env = [
        ...environment,
        null
    ];
    lib.execvpe(program, arr, env);
    // Program should be dead after this point.
    throw Error("execvpe failed to make the switch");
}

function find_inode(proc_net_tcp_lines) {
    const index_inode = proc_net_tcp_lines[0].indexOf('inode');
    const index_local_address = proc_net_tcp_lines[0].indexOf('local_address');
    for (const line of proc_net_tcp_lines.slice(1)) {
        const [address] = line.substr(index_local_address).split(' ', 1);
        const tentative_port = parseInt(address.split(':', 2)[1], 16);
        if (tentative_port === port) {
            const [inode] = line.substr(index_inode).split(' ', 1);
            return inode
        }
    }
    return null;
}


function locate_fd(port) {
    let inode = null;
    if (fs.existsSync(`/proc/${process.pid}/net/tcp6`)) {
        const data = fs.readFileSync(`/proc/${process.pid}/net/tcp6`, 'utf8');
        const lines = data.split('\n');
        inode = find_inode(lines);
    } else if (fs.existsSync(`/proc/${process.pid}/net/tcp`)) {
        const data = fs.readFileSync(`/proc/${process.pid}/net/tcp`, 'utf8');
        const lines = data.split('\n');
        inode = find_inode(lines);
    } else {
        const all_proc = fs.readdirSync(`/proc`);
        const current_process_proc = fs.readdirSync(`/proc/${process.pid}`);
        const process_one_proc = fs.readdirSync(`/proc/1`);
        console.error(`Could not locate network files`, {
            all_proc,
            process_one_proc,
            current_process_proc,
            pid: process.pid,
            argv: process.argv,
            env: process.env
        });
        return [null, 'net'];
    }
    if (inode === null) {
        console.error(`Could not locate promised open port: ${port}`);
        return [null, 'port'];
    }

    inode = parseInt(inode);

    const descriptors = fs.readdirSync('/proc/self/fd');
    for (const descriptor of descriptors) {
        const data = spawnSync('stat', [`/proc/${process.pid}/fd/${descriptor}`], {encoding: 'utf8'});
        if (data.stdout.includes(`socket:[${inode}]`)) {
            return [parseInt(descriptor), 'success']
        }
    }
    return [null, 'fail'];
}

function unsetCloseOnExec(descriptor) {
    const F_GETFD = 1;
    const F_SETFD = 2;
    const FD_CLOEXEC = 1;
    const flags = lib.fcntl(descriptor, F_GETFD, 0);
    lib.fcntl(descriptor, F_SETFD, (flags & ~FD_CLOEXEC));
}

function setBlockingMode(descriptor) {
    const F_GETFL = 3;
    const F_SETFL = 4;
    const O_NONBLOCK = 0o4000;
    const flags = lib.fcntl(descriptor, F_GETFL, 0);
    lib.fcntl(descriptor, F_SETFL, (flags & ~O_NONBLOCK));
}

function changeToPython(server_socket, load_socket) {
    // Drop the descriptor on the floor
    unsetCloseOnExec(server_socket);
    unsetCloseOnExec(load_socket);
    unsetCloseOnExec(0);
    unsetCloseOnExec(1);
    unsetCloseOnExec(2);
    //console.error('replacing with python now!', {descriptor});
    const pythonhome = `${process.cwd()}/python`;
    const app = `${pythonhome}/bin/python`;
    const args = ['-m', 'worker'];
    const env = [
        ...Object.keys(process.env).map(key => {
            return `${key}=${process.env[key]}`;
        }),
        `PYTHONHOME=${pythonhome}`,
        `PYTHONPATH=${pythonhome}`,
        `SERVER_DESCRIPTOR=${server_socket}`,
        `LOAD_DESCRIPTOR=${load_socket}`,
    ];
    // Close your eyes and forget all about node.
    execvpe(app, args, env);
}

const port = parseInt(process.env.X_GOOGLE_WORKER_PORT);
const output = fs.readdirSync('/proc/self/fdinfo');
let sockets = output.map(d => {
    try {
        const data = spawnSync('stat', [`/proc/${process.pid}/fd/${d}`], {encoding: 'utf8'});
        if (data.stdout.includes('socket')) {
            return d;
        }
    } catch (err) {
    }
    return null;
}).filter(s => s !== null).map(s => parseInt(s)).sort((a,b) => a-b);

console.log(`Descriptors: ${output.length} - Sockets: ${sockets.length}`);
const [descriptor, load_socket] = [sockets[0], sockets.slice(-1)[0]];
console.log("Queueing for python to take over.");
changeToPython(descriptor, load_socket);

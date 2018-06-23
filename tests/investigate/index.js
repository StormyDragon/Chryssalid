const fs = require('fs');

exports.investigate = (req, res) => {
    console.log('', {env: process.env, argv: process.argv});
    fs.readFile('/var/tmp/worker/worker.js', 'utf8', function(err, data) {
        if (err) throw err;
        res.status(200).send(data);
    });
};

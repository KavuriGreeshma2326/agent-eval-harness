#!/bin/bash
# The port is overridden by conf.d/90-local.ini, which is read after app.ini.
# Change it there; host and workers in the same file must stay as they are.
sed -i 's/^port = 9090$/port = 8080/' /app/config/conf.d/90-local.ini

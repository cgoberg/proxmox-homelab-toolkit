    # BEGIN FORGE PATCH: sensors
    eval {
        require JSON;
        my $sensors_json = `/usr/local/bin/forge-pve-sensors 2>/dev/null`;
        if (defined $sensors_json && length($sensors_json) > 2) {
            my $sensors = JSON::decode_json($sensors_json);
            $res->{forge_sensors} = $sensors if ref($sensors) eq 'HASH';
        }
    };
    # END FORGE PATCH: sensors

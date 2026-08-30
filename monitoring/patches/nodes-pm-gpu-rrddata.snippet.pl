# BEGIN FORGE PATCH: gpu_rrddata
__PACKAGE__->register_method({
    name => 'gpu_rrddata',
    path => 'gpu_rrddata',
    method => 'GET',
    protected => 1,
    permissions => {
        check => ['perm', '/nodes/{node}', ['Sys.Audit']],
    },
    description => "Read node GPU RRD statistics (forge custom).",
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            timeframe => {
                description => "Specify the time frame you are interested in.",
                type => 'string',
                enum => ['hour', 'day', 'week', 'month', 'year', 'decade'],
            },
            cf => {
                description => "The RRD consolidation function",
                type => 'string',
                enum => ['AVERAGE', 'MAX'],
                optional => 1,
            },
        },
    },
    returns => {
        type => "array",
        items => {
            type => "object",
            properties => {},
        },
    },
    code => sub {
        my ($param) = @_;
        my $rrd = "forge-gpu-9.0/$param->{node}";
        my $base = "/var/lib/rrdcached/db/$rrd";
        # If the RRD doesn't exist yet (collector not running / first boot),
        # return an empty array so the chart shows "No Data" instead of an
        # error.
        return [] unless -e $base;
        return PVE::RRD::create_rrd_data($rrd, $param->{timeframe}, $param->{cf});
    },
});
# END FORGE PATCH: gpu_rrddata

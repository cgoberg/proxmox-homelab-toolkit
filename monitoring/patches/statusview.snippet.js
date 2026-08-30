        // BEGIN FORGE PATCH: sensor rows
        {
            xtype: 'box',
            colspan: 2,
            padding: '0 0 10 0',
        },
        {
            itemId: 'forge-cpu-temp',
            colspan: 2,
            iconCls: 'fa fa-fw fa-thermometer-half',
            printBar: false,
            title: gettext('CPU temperature'),
            multiField: true,
            renderer: ({ data }) => {
                const t = data?.forge_sensors?.cpu_temp_c;
                return Ext.isNumeric(t) ? `${t.toFixed(1)} °C` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-gpu-temp',
            colspan: 2,
            iconCls: 'fa fa-fw fa-thermometer-three-quarters',
            printBar: false,
            title: gettext('GPU temperature'),
            multiField: true,
            renderer: ({ data }) => {
                const t = data?.forge_sensors?.gpu_temp_c;
                return Ext.isNumeric(t) ? `${t.toFixed(1)} °C` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-nvme-temp',
            colspan: 2,
            iconCls: 'fa fa-fw fa-thermometer-quarter',
            printBar: false,
            title: gettext('NVMe temperature'),
            multiField: true,
            renderer: ({ data }) => {
                const t = data?.forge_sensors?.nvme_temp_c;
                return Ext.isNumeric(t) ? `${t.toFixed(1)} °C` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-sata-temp',
            colspan: 2,
            iconCls: 'fa fa-fw fa-hdd-o',
            printBar: false,
            title: gettext('SATA SSD temperature'),
            multiField: true,
            renderer: ({ data }) => {
                const t = data?.forge_sensors?.sata_temp_c;
                return Ext.isNumeric(t) ? `${t.toFixed(1)} °C` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-mobo-temp',
            colspan: 2,
            iconCls: 'fa fa-fw fa-thermometer-empty',
            printBar: false,
            title: gettext('Motherboard temperature'),
            multiField: true,
            renderer: ({ data }) => {
                const t = data?.forge_sensors?.mobo_temp_c;
                return Ext.isNumeric(t) ? `${t.toFixed(1)} °C` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-gpu-usage',
            colspan: 2,
            iconCls: 'fa fa-fw fa-microchip',
            printBar: false,
            title: gettext('GPU usage'),
            multiField: true,
            renderer: ({ data }) => {
                const u = data?.forge_sensors?.gpu_usage_pct;
                return Ext.isNumeric(u) ? `${u.toFixed(1)} %` : Proxmox.Utils.unknownText;
            },
            value: '',
        },
        {
            itemId: 'forge-gpu-vram',
            colspan: 2,
            iconCls: 'fa fa-fw fa-database',
            printBar: false,
            title: gettext('GPU VRAM'),
            multiField: true,
            renderer: ({ data }) => {
                const u = data?.forge_sensors?.gpu_mem_used_mib;
                const t = data?.forge_sensors?.gpu_mem_total_mib;
                if (!Ext.isNumeric(u) || !Ext.isNumeric(t) || t <= 0) {
                    return Proxmox.Utils.unknownText;
                }
                const pct = (u / t) * 100;
                return `${u.toFixed(0)} / ${t.toFixed(0)} MiB (${pct.toFixed(1)} %)`;
            },
            value: '',
        },
        // END FORGE PATCH: sensor rows

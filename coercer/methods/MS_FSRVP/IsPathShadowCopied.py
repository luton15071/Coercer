#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File name          : IsPathShadowCopied.py
# Author             : Podalirius (@podalirius_)
# Date created       : 15 Sep 2022

from coercer.models.MSPROTOCOLRPCCALL import MSPROTOCOLRPCCALL
from coercer.network.DCERPCSessionError import DCERPCSessionError
from impacket.dcerpc.v5.ndr import NDRCALL, NDRSTRUCT
from impacket.dcerpc.v5.dtypes import UUID, ULONG, WSTR, DWORD, LONG, NULL, BOOL, UCHAR, PCHAR, RPC_SID, LPWSTR, GUID


class _IsPathShadowCopied(NDRCALL):
    opnum = 9
    structure = (
        ('ShareName', WSTR),  # Type: LPWSTR
    )


class _IsPathShadowCopiedResponse(NDRCALL):
    structure = ()


class IsPathShadowCopied(MSPROTOCOLRPCCALL):
    """

    """

    access = {
        "ncan_np": [
            {
                "namedpipe": r"\PIPE\Fssagentrpc",
                "uuid": "a8e0653c-2744-4389-a61d-7373df8b2292",
                "version": "1.0"
            }
        ]
    }

    protocol = {
        "longname": "[MS-FSRVP]: File Server Remote VSS Protocol",
        "shortname": "MS-FSRVP"
    }

    function = {
        "name": "IsPathShadowCopied",
        "opnum": 9,
        "vulnerable_arguments": ["ShareName"]
    }

    def trigger(self, dcerpc_session, target):
        if dcerpc_session is not None:
            try:
                request = _IsPathShadowCopied()
                request['ShareName'] = self.path
                resp = dcerpc_session.request(request)
                return ""
            except Exception as err:
                return err
        else:
            print("[!] Error: dce is None, you must call connect() first.")
            return None

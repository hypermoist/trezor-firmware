<%
networks = list(supported_on("trezor1", eth))
max_chain_id_length = 0
max_slip44_length = 0
max_suffix_length = 0
for n in networks:
	max_chain_id_length = max(len(str(n.chain_id)), max_chain_id_length)
	max_slip44_length = max(len(str(n.slip44)), max_slip44_length)
	max_suffix_length = max(len(n.shortcut), max_suffix_length)

def align_chain_id(n):
	return "{:>{w}}".format(n.chain_id, w=max_chain_id_length)

def align_slip44(n):
	return "{:>{w}}".format(n.slip44, w=max_slip44_length)

def align_suffix(n):
	cstr = c_str(" " + n.shortcut) + ";"
	# we add two quotes, a space and a semicolon. hence +4 chars
	return "{:<{w}}".format(cstr, w=max_suffix_length + 4)

%>\
// This file is automatically generated from ethereum_networks.c.mako
// DO NOT EDIT

#include "ethereum_networks.h"

const char *get_ethereum_suffix(uint64_t chain_id) {
  switch (chain_id) {
% for n in networks:
    case ${align_chain_id(n)}: return ${align_suffix(n)}  /* ${n.name} */
% endfor
    default: return UNKNOWN_NETWORK_SHORTCUT;  /* unknown chain */
  }
}

// TODO: do we need this functions?
bool is_ethereum_slip44(uint32_t slip44) {
  switch (slip44) {
% for slip44 in sorted(set(n.slip44 for n in networks)):
    case ${slip44}:
% endfor
      return true;
    default:
      return false;
  }
}

int32_t ethereum_slip44_by_chain_id(uint64_t chain_id) {
  switch (chain_id) {
% for n in networks:
    case ${align_chain_id(n)}: return ${align_slip44(n)};  /* ${n.name} */
% endfor
    default: return SLIP44_UNKNOWN;  /* unknown chain */
  }
}
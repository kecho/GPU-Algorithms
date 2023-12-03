import coalpy.gpu as g
from . import utilities as utils

g_group_size = 64
g_batch_size = 128
g_bits_per_radix = 8
g_bytes_per_radix = int(g_bits_per_radix/8)
g_radix_counts = int(32 / g_bits_per_radix)

g_count_scatter_shader = g.Shader(file = "radix_sort.hlsl", main_function = "csCountScatterBuckets")

def allocate_args(input_counts):
    aligned_batch_count = utils.alignup(input_counts, g_batch_size)
    perform_reduction = True
    
    c = aligned_batch_count
    count_table_count = 0

    while perform_reduction:
        count_table_count += utils.alignup(c, g_group_size)
        c = utils.divup(c, g_group_size)
        perform_reduction = c > 1

    count_table_count = count_table_count * g_radix_counts
    return (
        g.Buffer(name="localOffsets", element_count = input_counts, format = g.Format.R32_UINT),
        g.Buffer(name="pingBuffer", element_count = input_counts, format = g.Format.R32_UINT),
        g.Buffer(name="pongBuffer", element_count = input_counts, format = g.Format.R32_UINT),
        g.Buffer(name="countTableBuffer", element_count = count_table_count, format = g.Format.R32_UINT),
        input_counts)

def run (cmd_list, input_buffer, sort_args):
    (local_offsets, ping_buffer, pong_buffer, count_table, input_counts) = sort_args
    batch_counts = utils.divup(input_counts, g_batch_size)

    radix_i = 0
    radix_mask = int((1 << g_bits_per_radix) - 1)
    radix_shift = g_bits_per_radix * radix_i
    
    cmd_list.dispatch(
        x = batch_counts, y = 1, z = 1,
        shader = g_count_scatter_shader,
        inputs = input_buffer,
        outputs = [ local_offsets, count_table ],
        constants = [
            int(input_counts), batch_counts, radix_mask, radix_shift,
            g_batch_size, int(0), int(0), int(0) ]
    ) 

    return (local_offsets, count_table)

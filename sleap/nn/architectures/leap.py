"""This module provides a generalized implementation of the LEAP CNN.

See the `LeapCNN` class docstring for more information.
"""

import attr
from typing import List

from sleap.nn.architectures import encoder_decoder


@attr.s(auto_attribs=True)
class LeapCNN(encoder_decoder.EncoderDecoder):
    """LEAP CNN from "Fast animal pose estimation using deep neural networks" (2019).

    This is a simple encoder-decoder style architecture without skip connections.

    This implementation is generalized from original paper (`Pereira et al., 2019
    <https://www.nature.com/articles/s41592-018-0234-5>`_) and `code
    <https://github.com/talmo/leap>`_.

    Using the defaults will create a network with ~10.8M parameters.

    Attributes:
        filters: Base number of filters in the first encoder block. More filters will
            increase the representational capacity of the network at the cost of memory
            and runtime.
        filters_rate: Factor to increase the number of filters by in each block.
        down_blocks: Number of blocks with pooling in the encoder. More down blocks will
            increase the effective maximum receptive field, but may incur loss of
            spatial precision.
        down_convs_per_block: Number of convolutions in each encoder block. More
            convolutions per block will increase the representational capacity of the
            network at the cost of memory and runtime.
        up_blocks: Number of blocks with upsampling in the decoder. If this is equal to
            `down_blocks`, the output of this network will be at the same stride (scale)
            as the input.
        up_interpolate: If True, use bilinear interpolation instead of transposed
            convolutions for upsampling. Interpolation is faster but transposed
            convolutions may be able to learn richer or more complex upsampling to
            recover details from higher scales. If using transposed convolutions, the
            number of filters are determined by `filters` and `filters_rate` to
            progressively decrease the number of filters at each step.
        up_convs_per_block: Number of convolution layers after each upsampling
            operation. These will use the `filters` and `filters_rate` to progressively
            decrease the number of filters at each step.
    """

    filters: int = 64
    filters_rate: float = 2

    down_blocks: int = 3
    down_convs_per_block: int = 3

    up_blocks: int = 3
    up_interpolate: bool = False
    up_convs_per_block: int = 2

    @property
    def encoder_stack(self) -> List[encoder_decoder.SimpleConvBlock]:
        """Return the encoder block configuration."""
        blocks = []
        for i in range(self.down_blocks):
            blocks.append(
                encoder_decoder.SimpleConvBlock(
                    num_convs=self.down_convs_per_block,
                    filters=self.filters * (self.filters_rate ** i),
                    kernel_size=3,
                    use_bias=True,
                    batch_norm=False,
                    activation="relu",
                    pooling_stride=2,
                )
            )
        return blocks

    @property
    def decoder_stack(self) -> List[encoder_decoder.SimpleUpsamplingBlock]:
        """Return the decoder block configuration."""
        blocks = []
        for i in range(self.up_blocks, 0, -1):
            block_filters = self.filters * (self.filters_rate ** i)
            blocks.append(
                encoder_decoder.SimpleUpsamplingBlock(
                    upsampling_stride=2,
                    transposed_conv=(not self.up_interpolate),
                    transposed_conv_filters=block_filters,
                    transposed_conv_use_bias=True,
                    transposed_conv_kernel_size=3,
                    transposed_conv_batch_norm=False,
                    transposed_conv_activation="relu",
                    interp_method="bilinear",
                    skip_connection=False,
                    refine_convs=self.up_convs_per_block,
                    refine_convs_filters=block_filters,
                    refine_convs_kernel_size=3,
                    refine_convs_batch_norm=False,
                    refine_convs_activation="relu",
                )
            )
        return blocks
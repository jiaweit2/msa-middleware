import tensorflow as tf
import numpy as np

_BATCH_NORM_DECAY = 0.997
_BATCH_NORM_EPSILON = 1e-5


# -------------------Helper functions-------------------


def hw_flatten(x):
    x_shape = x.get_shape().as_list()
    return tf.reshape(x, shape=[-1, x_shape[1] * x_shape[2], x_shape[3]])


def batch_norm(inputs, training, data_format):
    """Performs a batch normalization using a standard set of parameters."""
    # We set fused=True for a significant performance boost. See
    # https://www.tensorflow.org/performance/performance_guide#common_fused_ops
    return tf.layers.batch_normalization(
        inputs=inputs,
        axis=1 if data_format == "channels_first" else 3,
        momentum=_BATCH_NORM_DECAY,
        epsilon=_BATCH_NORM_EPSILON,
        center=True,
        scale=True,
        training=training,
        fused=True,
    )


def spectral_norm(w, iteration=1):
    w_shape = w.shape.as_list()
    w = tf.reshape(w, [-1, w_shape[-1]])

    u = tf.get_variable(
        "u",
        [1, w_shape[-1]],
        initializer=tf.random_normal_initializer(),
        trainable=False,
    )

    u_hat = u
    v_hat = None
    for i in range(iteration):
        """
        power iteration
        Usually iteration = 1 will be enough
        """

        v_ = tf.matmul(u_hat, tf.transpose(w))
        v_hat = tf.nn.l2_normalize(v_)

        u_ = tf.matmul(v_hat, w)
        u_hat = tf.nn.l2_normalize(u_)

    u_hat = tf.stop_gradient(u_hat)
    v_hat = tf.stop_gradient(v_hat)

    sigma = tf.matmul(tf.matmul(v_hat, w), tf.transpose(u_hat))

    with tf.control_dependencies([u.assign(u_hat)]):
        w_norm = w / sigma
        w_norm = tf.reshape(w_norm, w_shape)

    return w_norm


def conv(
    x,
    channels,
    kernel=4,
    stride=2,
    pad=0,
    pad_type="zero",
    use_bias=True,
    sn=False,
    data_format=None,
    scope="conv_0",
):
    with tf.variable_scope(scope):
        if pad > 0:
            h = x.get_shape().as_list()[2]
            if h % stride == 0:
                pad = pad * 2
            else:
                pad = max(kernel - (h % stride), 0)

            pad_top = pad // 2
            pad_bottom = pad - pad_top
            pad_left = pad // 2
            pad_right = pad - pad_left

            if data_format == "channels_first":
                if pad_type == "zero":
                    x = tf.pad(
                        x,
                        [[0, 0], [0, 0], [pad_top, pad_bottom], [pad_left, pad_right]],
                    )
                if pad_type == "reflect":
                    x = tf.pad(
                        x,
                        [[0, 0], [0, 0], [pad_top, pad_bottom], [pad_left, pad_right]],
                        mode="REFLECT",
                    )
            else:
                if pad_type == "zero":
                    x = tf.pad(
                        x,
                        [[0, 0], [pad_top, pad_bottom], [pad_left, pad_right], [0, 0]],
                    )
                if pad_type == "reflect":
                    x = tf.pad(
                        x,
                        [[0, 0], [pad_top, pad_bottom], [pad_left, pad_right], [0, 0]],
                        mode="REFLECT",
                    )

        weight_init = tf.truncated_normal_initializer(mean=0.0, stddev=0.02)
        weight_regularizer = orthogonal_regularizer(0.0001, data_format)
        if sn:
            if data_format == "channels_first":
                w = tf.get_variable(
                    "kernel",
                    shape=[kernel, kernel, x.get_shape()[1], channels],
                    initializer=weight_init,
                    regularizer=weight_regularizer,
                )
                x = tf.nn.conv2d(
                    input=x,
                    filter=spectral_norm(w),
                    strides=[1, 1, stride, stride],
                    padding="VALID",
                    data_format="NCHW",
                )
            else:
                w = tf.get_variable(
                    "kernel",
                    shape=[kernel, kernel, x.get_shape()[-1], channels],
                    initializer=weight_init,
                    regularizer=weight_regularizer,
                )
                x = tf.nn.conv2d(
                    input=x,
                    filter=spectral_norm(w),
                    strides=[1, stride, stride, 1],
                    padding="VALID",
                    data_format="NHWC",
                )
            if use_bias:
                bias = tf.get_variable(
                    "bias", [channels], initializer=tf.constant_initializer(0.0)
                )
                if data_format == "channels_first":
                    x = tf.nn.bias_add(x, bias, data_format="NCHW")
                else:
                    x = tf.nn.bias_add(x, bias, data_format="NHWC")
        else:
            x = tf.layers.conv2d(
                inputs=x,
                filters=channels,
                kernel_size=kernel,
                kernel_initializer=weight_init,
                kernel_regularizer=weight_regularizer,
                strides=stride,
                use_bias=use_bias,
                data_format=data_format,
            )
    return x


def deconv(
    x,
    channels,
    kernel=4,
    stride=2,
    padding="SAME",
    use_bias=True,
    sn=False,
    data_format=None,
    scope="deconv_0",
):
    with tf.variable_scope(scope):
        x_shape = x.get_shape().as_list()
        if data_format == "channels_first":
            if padding == "SAME":
                output_shape = [
                    tf.shape(x)[0],
                    channels,
                    x_shape[2] * stride,
                    x_shape[3] * stride,
                ]
            else:
                output_shape = [
                    tf.shape(x)[0],
                    channels,
                    x_shape[2] * stride + max(kernel - stride, 0),
                    x_shape[3] * stride + max(kernel - stride, 0),
                ]
        else:
            if padding == "SAME":
                output_shape = [
                    tf.shape(x)[0],
                    x_shape[1] * stride,
                    x_shape[2] * stride,
                    channels,
                ]
            else:
                output_shape = [
                    tf.shape(x)[0],
                    x_shape[1] * stride + max(kernel - stride, 0),
                    x_shape[2] * stride + max(kernel - stride, 0),
                    channels,
                ]
        # print('output_shape', output_shape)
        weight_init = tf.truncated_normal_initializer(mean=0.0, stddev=0.02)
        weight_regularizer = orthogonal_regularizer(0.0001, data_format)
        if sn:
            if data_format == "channels_first":
                w = tf.get_variable(
                    "kernel",
                    shape=[kernel, kernel, channels, x.get_shape().as_list()[1]],
                    initializer=weight_init,
                    regularizer=weight_regularizer,
                )
                x = tf.nn.conv2d_transpose(
                    x,
                    filter=spectral_norm(w),
                    output_shape=output_shape,
                    strides=[1, 1, stride, stride],
                    padding=padding,
                    data_format="NCHW",
                )
            else:
                w = tf.get_variable(
                    "kernel",
                    shape=[kernel, kernel, channels, x.get_shape().as_list()[-1]],
                    initializer=weight_init,
                    regularizer=weight_regularizer,
                )
                x = tf.nn.conv2d_transpose(
                    x,
                    filter=spectral_norm(w),
                    output_shape=output_shape,
                    strides=[1, stride, stride, 1],
                    padding=padding,
                    data_format="NHWC",
                )
            if use_bias:
                bias = tf.get_variable(
                    "bias", [channels], initializer=tf.constant_initializer(0.0)
                )
                if data_format == "channels_first":
                    x = tf.nn.bias_add(x, bias, data_format="NCHW")
                else:
                    x = tf.nn.bias_add(x, bias, data_format="NHWC")
        else:
            x = tf.layers.conv2d_transpose(
                inputs=x,
                filters=channels,
                kernel_size=kernel,
                kernel_initializer=weight_init,
                kernel_regularizer=weight_regularizer,
                strides=stride,
                padding=padding,
                use_bias=use_bias,
                data_format=data_format,
            )
        return x


def orthogonal_regularizer(scale, data_format):
    """ Defining the Orthogonal regularizer and return the function at last to be used in Conv layer as kernel regularizer"""

    def ortho_reg(w):
        """ Reshaping the matrxi in to 2D tensor for enforcing orthogonality"""
        # if data_format == 'channels_first':
        # 	_, c, _, _ = w.get_shape().as_list()
        # else:
        # 	_, _, _, c = w.get_shape().as_list()
        if data_format == "channels_first":
            w = tf.transpose(w, [0, 2, 3, 1])
        _, _, _, c = w.get_shape().as_list()
        w = tf.reshape(w, [-1, c])

        """ Declaring a Identity Tensor of appropriate size"""
        identity = tf.eye(c)

        """ Regularizer Wt*W - I """
        w_transpose = tf.transpose(w)
        w_mul = tf.matmul(w_transpose, w)
        reg = tf.subtract(w_mul, identity)

        """Calculating the Loss Obtained"""
        ortho_loss = tf.nn.l2_loss(reg)

        return scale * ortho_loss

    return


def self_attention_full(
    x, channels, sn=False, data_format=None, scope="self_attention"
):
    with tf.variable_scope(scope):
        # print('atten_in', x.get_shape())
        weight_init = tf.truncated_normal_initializer(mean=0.0, stddev=0.02)
        weight_regularizer = orthogonal_regularizer(0.0001, data_format)
        with tf.variable_scope("f_conv"):
            f = conv(x, channels, kernel=1, stride=1, sn=sn, data_format=data_format)
            f = tf.layers.max_pooling2d(
                f, pool_size=4, strides=4, padding="SAME", data_format=data_format
            )
            if data_format == "channels_first":
                f = tf.transpose(f, [0, 2, 3, 1])
        with tf.variable_scope("g_conv"):
            g = conv(x, channels, kernel=1, stride=1, sn=sn, data_format=data_format)
            if data_format == "channels_first":
                g = tf.transpose(g, [0, 2, 3, 1])
        with tf.variable_scope("h_conv"):
            h = conv(x, channels, kernel=1, stride=1, sn=sn, data_format=data_format)
            h = tf.layers.max_pooling2d(
                h, pool_size=4, strides=4, padding="SAME", data_format=data_format
            )
            if data_format == "channels_first":
                h = tf.transpose(h, [0, 2, 3, 1])

        s = tf.matmul(hw_flatten(g), hw_flatten(f), transpose_b=True)
        beta = tf.nn.softmax(s)  # attention map
        o = tf.matmul(beta, hw_flatten(h))
        gamma = tf.get_variable("gamma", [1], initializer=tf.constant_initializer(0.0))
        if data_format == "channels_first":
            o = tf.transpose(o, [0, 2, 1])

        x_shape = x.get_shape().as_list()
        if data_format == "channels_first":
            o = tf.reshape(o, shape=[-1, channels, x_shape[2], x_shape[3]])
        else:
            o = tf.reshape(o, shape=[-1, x_shape[1], x_shape[2], channels])

        o = conv(
            o,
            channels,
            kernel=1,
            stride=1,
            sn=sn,
            data_format=data_format,
            scope="attn_conv",
        )
        x = gamma * o + x
        return x


def resblock_up(
    x_init,
    channels,
    use_bias=True,
    is_training=True,
    sn=False,
    data_format=None,
    scope="resblock_up",
):
    with tf.variable_scope(scope):
        with tf.variable_scope("res1"):
            x = batch_norm(x_init, is_training, data_format)
            x = tf.nn.relu(x)
            x = deconv(
                x,
                channels,
                kernel=3,
                stride=2,
                use_bias=use_bias,
                sn=sn,
                data_format=data_format,
            )
        with tf.variable_scope("res2"):
            x = batch_norm(x, is_training, data_format)
            x = tf.nn.relu(x)
            x = deconv(
                x,
                channels,
                kernel=3,
                stride=1,
                use_bias=use_bias,
                sn=sn,
                data_format=data_format,
            )
        with tf.variable_scope("skip"):
            x_init = deconv(
                x_init,
                channels,
                kernel=3,
                stride=2,
                use_bias=use_bias,
                sn=sn,
                data_format=data_format,
            )
    return x + x_init


def self_attention_2(x, channels, sn=False, data_format=None, scope="self_attention"):
    with tf.variable_scope(scope):
        # print('atten_in', x.get_shape())
        weight_init = tf.truncated_normal_initializer(mean=0.0, stddev=0.02)
        weight_regularizer = orthogonal_regularizer(0.0001, data_format)
        with tf.variable_scope("f_conv"):
            f = conv(
                x, channels // 8, kernel=1, stride=1, sn=sn, data_format=data_format
            )
            f = tf.layers.max_pooling2d(
                f, pool_size=8, strides=8, padding="SAME", data_format=data_format
            )
            if data_format == "channels_first":
                f = tf.transpose(f, [0, 2, 3, 1])
            # print('f', f.get_shape(), channels // 8)
        with tf.variable_scope("g_conv"):
            g = conv(
                x, channels // 8, kernel=1, stride=1, sn=sn, data_format=data_format
            )
            if data_format == "channels_first":
                g = tf.transpose(g, [0, 2, 3, 1])
            # print('g', g.get_shape(), channels // 8)
        with tf.variable_scope("h_conv"):
            h = conv(
                x, channels // 4, kernel=1, stride=1, sn=sn, data_format=data_format
            )
            # h = tf.layers.max_pooling2d(h, pool_size=6, strides=6, padding='SAME',
            # 												   data_format=data_format)
            h = tf.layers.max_pooling2d(
                h, pool_size=8, strides=8, padding="SAME", data_format=data_format
            )
            if data_format == "channels_first":
                h = tf.transpose(h, [0, 2, 3, 1])
            # print('h', h.get_shape(), channels // 4)

        s = tf.matmul(hw_flatten(g), hw_flatten(f), transpose_b=True)
        beta = tf.nn.softmax(s)  # attention map
        o = tf.matmul(beta, hw_flatten(h))
        gamma = tf.get_variable("gamma", [1], initializer=tf.constant_initializer(0.0))
        if data_format == "channels_first":
            o = tf.transpose(o, [0, 2, 1])

        x_shape = x.get_shape().as_list()
        if data_format == "channels_first":
            o = tf.reshape(o, shape=[-1, channels // 4, x_shape[2], x_shape[3]])
        else:
            o = tf.reshape(o, shape=[-1, x_shape[1], x_shape[2], channels // 4])

        o = conv(
            o,
            channels,
            kernel=1,
            stride=1,
            sn=sn,
            data_format=data_format,
            scope="attn_conv",
        )
        x = gamma * o + x
        return x


# -------------------Encoder / Decoder-------------------


def encode(
    inter_rep,
    compress_ratio=0.05,
    spectral_norm=spectral_norm,
    data_format="channels_last",
):
    with tf.variable_scope("endecoder") as scope:
        axes = [2, 3] if data_format == "channels_first" else [1, 2]

        out_size = max(int(3 * compress_ratio * 4 * 4), 1)
        print("out_size", out_size)

        c_sample = conv(
            inter_rep,
            out_size,
            kernel=3,
            stride=4,
            sn=spectral_norm,
            use_bias=False,
            data_format=data_format,
            scope="samp_conv",
        )

        num_centers = 8
        quant_centers = tf.get_variable(
            "quant_centers",
            shape=(num_centers,),
            dtype=tf.float32,
            initializer=tf.random_uniform_initializer(minval=-16.0, maxval=16),
        )

        # print("quant_centers", quant_centers)
        # print("c_sample", c_sample)
        quant_dist = tf.square(
            tf.abs(tf.expand_dims(c_sample, axis=-1) - quant_centers)
        )
        phi_soft = tf.nn.softmax(-1.0 * quant_dist, dim=-1)
        symbols_hard = tf.argmax(phi_soft, axis=-1)
        phi_hard = tf.one_hot(
            symbols_hard, depth=num_centers, axis=-1, dtype=tf.float32
        )
        softout = tf.reduce_sum(phi_soft * quant_centers, -1)
        hardout = tf.reduce_sum(phi_hard * quant_centers, -1)

        c_sample_q = softout + tf.stop_gradient(hardout - softout)

        # print("phi_soft", phi_soft)
        # print("phi_hard", phi_hard)
        # print("quant_dist", quant_dist)
        # print("softout", softout)
        # print("hardout", hardout)
        # print("c_sample_q", c_sample_q)
        return c_sample_q


def decode(
    c_sample_q,
    compress_ratio=0.05,
    spectral_norm=spectral_norm,
    training=False,
    data_format="channels_last",
):
    with tf.variable_scope("endecoder") as scope:
        out_size = max(int(3 * compress_ratio * 4 * 4), 1)

        c_recon = self_attention_full(
            c_sample_q,
            channels=out_size,
            sn=spectral_norm,
            data_format=data_format,
            scope="self_attention1",
        )
        c_recon = resblock_up(
            c_recon,
            channels=64,
            use_bias=False,
            is_training=training,
            sn=spectral_norm,
            data_format=data_format,
            scope="resblock_up_x2",
        )
        c_recon = self_attention_2(
            c_recon,
            channels=64,
            sn=spectral_norm,
            data_format=data_format,
            scope="self_attention2",
        )
        c_recon = resblock_up(
            c_recon,
            channels=32,
            use_bias=False,
            is_training=training,
            sn=spectral_norm,
            data_format=data_format,
            scope="resblock_up_x4",
        )

        c_recon = batch_norm(c_recon, training, data_format)
        c_recon = tf.nn.relu(c_recon)

        if data_format == "channels_first":
            c_recon = tf.pad(c_recon, tf.constant([[0, 0], [0, 0], [1, 1], [1, 1]]))
        else:
            c_recon = tf.pad(c_recon, tf.constant([[0, 0], [1, 1], [1, 1], [0, 0]]))
        c_recon = conv(
            c_recon,
            channels=3,
            kernel=3,
            stride=1,
            use_bias=False,
            sn=spectral_norm,
            data_format=data_format,
            scope="G_logit",
        )

        c_recon = tf.nn.tanh(c_recon)
        _R_MEAN = 123.68
        _G_MEAN = 116.78
        _B_MEAN = 103.94
        _CHANNEL_MEANS = [_R_MEAN, _G_MEAN, _B_MEAN]
        if data_format == "channels_first":
            ch_means = tf.expand_dims(
                tf.expand_dims(tf.expand_dims(_CHANNEL_MEANS, 0), 2), 3
            )
        else:
            ch_means = tf.expand_dims(
                tf.expand_dims(tf.expand_dims(_CHANNEL_MEANS, 0), 0), 0
            )
        return (c_recon + 1.0) * 127.5 - ch_means


if __name__ == "__main__":
    import cv2

    data_format = "channels_first" if tf.test.is_built_with_cuda() else "channels_last"
    image_url = "/Users/mike/Desktop/img.png"
    img = cv2.imread(image_url)

    original_img = tf.convert_to_tensor(frame)
    sample = encode(tensor)
    decoded_img = decode(sample)

    cv2.imshow("test", decoded_img.numpy())
    cv2.waitKey(1000)

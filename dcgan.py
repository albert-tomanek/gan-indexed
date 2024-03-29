from __future__ import print_function, division

from keras.layers import Input, Dense, Permute, Reshape, Flatten, Dropout
from keras.layers import BatchNormalization, Activation, ZeroPadding2D
from keras.layers.advanced_activations import LeakyReLU
from keras.layers.convolutional import UpSampling2D, Conv2D
from keras.models import Sequential, Model
from keras.optimizers import Adam

from keras.datasets import fashion_mnist
import keras
from keras import backend as K

import matplotlib.pyplot as plt
import numpy as np
import sys

from indexed_img import *

class DCGAN():
    def __init__(self):
        # Input shape
        self.img_rows = 28
        self.img_cols = 28
        self.num_colors = 3
        self.img_shape = (self.img_rows, self.img_cols, self.num_colors)
        self.latent_dim = 100

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminator
        self.discriminator = self.build_discriminator()
        self.discriminator.compile(loss='binary_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])

        # Build the generator
        self.generator = self.build_generator()

        # The generator takes noise as input and generates imgs
        z = Input(shape=(self.latent_dim,))
        img = self.generator(z)

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # The discriminator takes generated images as input and determines validity
        valid = self.discriminator(img)

        # The combined model  (stacked generator and discriminator)
        # Trains the generator to fool the discriminator
        self.combined = Model(z, valid)
        self.combined.compile(loss='binary_crossentropy', optimizer=optimizer)

    def build_generator(self):

        model = Sequential()

        model.add(Dense(128 * 7 * 7, activation="relu", input_dim=self.latent_dim))
        model.add(Reshape((7, 7, 128)))
        model.add(UpSampling2D())
        model.add(Conv2D(128, kernel_size=3, padding="same"))
        model.add(BatchNormalization(momentum=0.8))
        model.add(Activation("relu"))
        model.add(UpSampling2D())
        model.add(Conv2D(64, kernel_size=3, padding="same"))
        model.add(BatchNormalization(momentum=0.8))
        model.add(Activation("relu"))
        model.add(Conv2D(self.num_colors, kernel_size=3, padding="same"))   # (3, 28, 28)
        model.add(Activation("sigmoid"))
        # model.add(Permute(()))

        model.summary()

        noise = Input(shape=(self.latent_dim,))
        img = model(noise)

        return Model(noise, img)

    def build_discriminator(self):

        model = Sequential()

        model.add(Conv2D(32, kernel_size=3, strides=2, input_shape=self.img_shape, padding="same"))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dropout(0.25))
        model.add(Conv2D(64, kernel_size=3, strides=2, padding="same"))
        model.add(ZeroPadding2D(padding=((0,1),(0,1))))
        model.add(BatchNormalization(momentum=0.8))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dropout(0.25))
        model.add(Conv2D(128, kernel_size=3, strides=2, padding="same"))
        model.add(BatchNormalization(momentum=0.8))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dropout(0.25))
        model.add(Conv2D(256, kernel_size=3, strides=1, padding="same"))
        model.add(BatchNormalization(momentum=0.8))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dropout(0.25))
        model.add(Flatten())
        model.add(Dense(1, activation='sigmoid'))

        model.summary()

        img = Input(shape=self.img_shape)
        validity = model(img)

        return Model(img, validity)

    def train(self, epochs, batch_size=128, save_interval=50):

        # Load the dataset
        (x_data, _), (_, _) = fashion_mnist.load_data()

        # Convert to grayscale indexed [0, 1, 2]
        x_data = x_data // 86                                 # Splits colors in 0-255 plain into 3 more-less equaly sized parts.
        x_data = keras.utils.to_categorical(x_data)     # One-hot encode

        # Adversarial ground truths
        valid = np.ones((batch_size, 1))
        fake = np.zeros((batch_size, 1))

        for epoch in range(epochs):

            # ---------------------
            #  Train Discriminator
            # ---------------------

            # Select a random half of images
            idx = np.random.randint(0, x_data.shape[0], batch_size)
            imgs = x_data[idx]

            # Sample noise and generate a batch of new images
            noise = np.random.normal(0, 1, (batch_size, self.latent_dim))
            gen_imgs = self.generator.predict(noise)

            # Train the discriminator (real classified as ones and generated as zeros)
            d_loss_real = self.discriminator.train_on_batch(imgs, valid)        # Teach that these images are valid
            d_loss_fake = self.discriminator.train_on_batch(gen_imgs, fake)     # Teach that these images are fake.
            d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

            # ---------------------
            #  Train Generator
            # ---------------------

            # Train the generator (wants discriminator to mistake images as real)
            g_loss = self.combined.train_on_batch(noise, valid)

            # Plot the progress
            print ("%d [D loss: %f, acc.: %.2f%%] [G loss: %f]" % (epoch, d_loss[0], 100*d_loss[1], g_loss))

            # If at save interval => save generated image samples
            if epoch % save_interval == 0:
                self.save_imgs(epoch)
                self.save_imgs_intensities(epoch)

    def save_imgs(self, epoch):
        r, c = 5, 5
        noise = np.random.normal(0, 1, (r * c, self.latent_dim))
        gen_imgs = self.generator.predict(noise)

        # Rescale images 0 - 1
        gen_imgs = idx_to_rgb(onehot_to_indexed(gen_imgs),
            np.array([[0, 0, 0], [.5, .5, .5], [1, 1, 1]])  # Grayscale palette
        )

        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(r):
            for j in range(c):
                axs[i,j].imshow(gen_imgs[cnt, :,:,0], cmap='gray')
                axs[i,j].axis('off')
                cnt += 1
        fig.savefig("images/fashion_mnist_%d.png" % epoch)
        plt.close()

    def save_imgs_intensities(self, epoch):
        r, c = 8, self.num_colors + 1
        noise = np.random.normal(0, 1, (r * c, self.latent_dim))
        gen_imgs = self.generator.predict(noise)

        chnl_intensities = gen_imgs.transpose((0, 3, 1, 2))     # (32, 28, 28, 3) -> (32, 3, 28, 28)    Splits into three separate heatmaps.

        # Rescale images 0 - 1
        gen_imgs = idx_to_rgb(onehot_to_indexed(gen_imgs),
            np.array([[0, 0, 0], [.5, .5, .5], [1, 1, 1]])  # Grayscale palette
        )

        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(r):
            axs[i,0].imshow(gen_imgs[cnt, :,:,0], cmap='gray')
            axs[i,0].axis('off')

            for chnl in range(self.num_colors):
                axs[i,chnl+1].imshow(chnl_intensities[cnt, chnl], cmap='gist_heat')
                axs[i,chnl+1].axis('off')

            cnt += 1
        fig.savefig("images/fashion_mnist_inten_%d.png" % epoch)
        plt.close()

    def save_weights(self, g='generator.h5', d='discriminator.h5'):
        self.generator.save_weights(g)
        self.discriminator.save_weights(d)

    def load_weights(self, g='generator.h5', d='discriminator.h5'):
        self.generator.load_weights(g)
        self.discriminator.load_weights(d)

import os

if __name__ == '__main__':
    dcgan = DCGAN()

    if os.path.exists('generator.h5'):
        dcgan.load_weights()

    try:
        dcgan.train(epochs=4000, batch_size=32, save_interval=50)
    finally:
        dcgan.save_weights()

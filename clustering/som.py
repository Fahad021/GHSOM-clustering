import tensorflow as tf
import numpy as np


class SOM(object):
    """
    2-D Self-Organizing Map with Gaussian Neighbourhood function
    and linearly decreasing learning rate.
    """

    #To check if the SOM has been trained
    _trained = False

    def __init__(self, m, n, dim, weight_after_insertion, n_iterations=42, alpha=None, sigma=None):
        """
        Initializes all necessary components of the TensorFlow
        Graph.

        m X n are the dimensions of the SOM. 'n_iterations' should
        should be an integer denoting the number of iterations undergone
        while training.
        'dim' is the dimensionality of the training inputs.
        'alpha' is a number denoting the initial time(iteration no)-based
        learning rate. Default value is 0.3
        'sigma' is the the initial neighbourhood value, denoting
        the radius of influence of the BMU while training. By default, its
        taken to be half of max(m, n).
        """

        #Assign required variables first
        self._m = m
        self._n = n
        if alpha is None:
            alpha = 0.3
        else:
            alpha = float(alpha)
        if sigma is None:
            sigma = max(m, n) / 2.0
        else:
            sigma = float(sigma)    #initial neighbourhood value
        self._n_iterations = abs(int(n_iterations))



        ##INITIALIZE GRAPH
        self._graph = tf.Graph()

        ##POPULATE GRAPH WITH NECESSARY COMPONENTS
        with self._graph.as_default():

            ##VARIABLES AND CONSTANT OPS FOR DATA STORAGE

            #Randomly initialized weightage vectors for all neurons,
            #stored together as a matrix Variable of size [m*n, dim]
            #Every node on output are fully connected to input (features)
            # API: tf.random_normal: Outputs random values from a normal distribution.
            if  weight_after_insertion is None:
                self._weightage_vects = tf.Variable(tf.random_normal(
                    [m*n, dim]))
            else:
                self._weightage_vects = tf.Variable(weight_after_insertion)


            #Matrix of size [m*n, 2] for SOM grid locations
            #of neurons
            self._location_vects = tf.constant(np.array(
                list(self._neuron_locations(m, n))))


            ##PLACEHOLDERS FOR TRAINING INPUTS
            #We need to assign them as attributes to self, since they
            #will be fed in during training

            #The training vector
            self._vect_input = tf.placeholder("float",  shape=[dim])
            #Iteration number
            self._iter_input = tf.placeholder("float")

            ##CONSTRUCT TRAINING OP PIECE BY PIECE
            #Only the final, 'root' training op needs to be assigned as
            #an attribute to self, since all the rest will be executed
            #automatically during training

            #To compute the Best Matching Unit given a vector
            #Basically calculates the Euclidean distance between every
            #neuron's weightage vector and the input, and returns the
            #index of the neuron which gives the least value
            # API:
            #   tf.argmin: Returns the index with the smallest value across axes of a tensor.
            #   tf.reduce_sum: second arg means reduce col axis
            #   tf.pow: Computes the power of one value to another. 2 means square
            #   tf.stack: Stacks a list of rank-R tensors into one rank-(R+1) tensor. rank1 tensor --> rank2 tensor
            bmu_index = tf.argmin(
                            tf.sqrt(
                                tf.reduce_sum(
                                    tf.pow(
                                        tf.subtract(
                                            self._weightage_vects,
                                            tf.stack([self._vect_input for i in range(m*n)])
                                            ),
                                    2),
                                1)),
                        0)

            #This will extract the location of the BMU based on the BMU's
            #index
            # API
            #  tf.pad: add padding to matrix, np.array([[0, 1]]) means add 1 element after bmu matrix
            slice_input = tf.pad(tf.reshape(bmu_index, [1]),
                                 np.array([[0, 1]]))
            # bmu_loc_1 = tf.slice(self._location_vects, slice_input,tf.constant(np.array([1, 2])))
            bmu_loc = tf.reshape(tf.slice(self._location_vects, slice_input,
                                          tf.cast(tf.constant(np.array([1, 2])), dtype=tf.int64)),
                                 [2])

            #To compute the alpha and sigma values based on iteration
            #number
            learning_rate_op = tf.subtract(1.0, tf.div(self._iter_input,
                                                  self._n_iterations))
            _alpha_op = tf.multiply(alpha, learning_rate_op)
            _sigma_op = tf.multiply(sigma, learning_rate_op)

            #Construct the op that will generate a vector with learning
            #rates for all neurons, based on iteration number and location
            #wrt BMU.
            # API:
            #   tf.cast: Casts a tensor to a new type.
            #   tf.negative: Computes numerical negative value element-wise.

            bmu_distance_squares = tf.reduce_sum(tf.pow(tf.subtract(
                self._location_vects, tf.stack(
                    [bmu_loc for i in range(m*n)])), 2), 1)
            neighbourhood_func = tf.exp(tf.negative(tf.div(tf.cast(
                bmu_distance_squares, "float32"), tf.pow(_sigma_op, 2))))
            learning_rate_op = tf.multiply(_alpha_op, neighbourhood_func)

            #Finally, the op that will use learning_rate_op to update
            #the weightage vectors of all neurons based on a particular
            #input
            #  API:
            #   tf.tile:  For example, tiling [a b c d] by [2] produces [a b c d a b c d]
            #   tf.assign: Update 'ref' by assigning 'value' to it.
            learning_rate_multiplier = tf.stack([tf.tile(tf.slice(
                learning_rate_op, np.array([i]), np.array([1])), [dim])
                                               for i in range(m*n)])


            # learning_rate_multiplier_1 = [tf.tile(tf.slice(
            #     learning_rate_op, np.array([1]), np.array([1])), [dim]) for i in range(m*n)]
            # learning_rate_multiplier_2 = tf.slice(
            #     learning_rate_op, np.array([1]), np.array([1]))
            # learning_rate_multiplier_3 = learning_rate_op, np.array([1])
            # learning_rate_multiplier_4 = np.array([1])


            weightage_delta = tf.multiply(
                learning_rate_multiplier,
                tf.subtract(tf.stack([self._vect_input for i in range(m*n)]),
                       self._weightage_vects))
            new_weightages_op = tf.add(self._weightage_vects,
                                       weightage_delta)
            self._training_op = tf.assign(self._weightage_vects,
                                          new_weightages_op)

            ##INITIALIZE SESSION
            self._sess = tf.Session()

            ##INITIALIZE VARIABLES
            init_op = tf.global_variables_initializer()
            self._sess.run(init_op)

            # print('------self._training_op---------')
            # print(self._sess.run(self._training_op,feed_dict={self._vect_input: input_data[0],self._iter_input: 1}))


    def _neuron_locations(self, m, n):
        """
        Yields one by one the 2-D locations of the individual neurons
        in the SOM.
        """
        #Nested iterations over both dimensions
        #to generate all 2-D locations in the map
        # result: Tensor("Const:0", shape=(49, 2), dtype=int64)
        for i in range(m):
            for j in range(n):
                yield np.array([i, j])

    def train(self, input_vects):
        """
        Trains the SOM.
        'input_vects' should be an iterable of 1-D NumPy arrays with
        dimensionality as provided during initialization of this SOM.
        Current weightage vectors for all neurons(initially random) are
        taken as starting conditions for training.
        """

        # Training iterations
        # for iter_no in range(self._n_iterations):
            # print('LoopNo: ' + str(iter_no) + ' - Time: ' + str(datetime.datetime.now().time()))
            #Train with each vector one by one

        print('SOM-Start')
        # for i in range(10):
        iter_no = 1
        for input_vect in input_vects:
            self._sess.run(self._training_op,
                           feed_dict={self._vect_input: input_vect,
                                      self._iter_input: iter_no})

            iter_no += 1
        # print('training end : ' + str(datetime.datetime.now()))


        # Store a centroid grid for easy retrieval later on
        # list() : converts to lists
        # enumerate:returns a iterator that will return (0, thing[0]), (1, thing[1]), (2, thing[2]), and so forth.
        centroid_grid = [[] for i in range(self._m)]
        self._weightages = list(self._sess.run(self._weightage_vects))

        self._locations = list(self._sess.run(self._location_vects))
        for i, loc in enumerate(self._locations):
            centroid_grid[loc[0]].append(self._weightages[i])
        self._centroid_grid = centroid_grid

        self._trained = True
        print('SOM-finish')
        return np.array(self._weightages)

    # def get_centroids(self):
    #     """
    #     Returns a list of 'm' lists, with each inner list containing
    #     the 'n' corresponding centroid locations as 1-D NumPy arrays.
    #     """
    #     if not self._trained:
    #         raise ValueError("SOM not trained yet")
    #     return self._centroid_grid

    def map_vects(self, input_vects):
        """
        Maps each input vector to the relevant neuron in the SOM
        grid.
        'input_vects' should be an iterable of 1-D NumPy arrays with
        dimensionality as provided during initialization of this SOM.
        Returns a list of 1-D NumPy arrays containing (row, column)
        info for each input vector(in the same order), corresponding
        to mapped neuron.
        """

        if not self._trained:
            raise ValueError("SOM not trained yet")

        to_return = []
        for vect in input_vects:
            min_index = min([i for i in range(len(self._weightages))],
                            key=lambda x: np.linalg.norm(vect-
                                                         self._weightages[x]))
            to_return.append(self._locations[min_index])

        return to_return

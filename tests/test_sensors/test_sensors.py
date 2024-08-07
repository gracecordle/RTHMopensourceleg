import numpy as np
import pytest
from pytest_mock import mocker

from opensourceleg.hardware.joints import Joint
from opensourceleg.hardware.sensors import Loadcell, StrainAmp
from opensourceleg.tools.logger import Logger
from tests.test_actuators.test_dephyactpack import Data
from tests.test_joints.test_joint import MockJoint, patch_sleep

LOADCELL_MATRIX = np.array(
    [
        (-35.44949, -1408.27600, 5.28557, -14.07667, 19.88193, 1413.95837),
        (-3.48398, 821.60516, -51.38681, 1630.13098, 42.46563, 823.29095),
        (-817.61768, -2.21026, -840.11005, -8.60509, -831.32318, -3.53086),
        (17.09737, 0.17497, 0.22292, -0.58087, -16.93312, -0.05286),
        (-9.28386, -0.30000, 20.22296, -0.07903, -9.65388, 0.34513),
        (-0.61599, -21.24456, -0.50275, 21.10707, -0.80625, -23.02333),
    ]
)


class MockSMBus:
    """
    Mocked SMBus class to test the StrainAmp class\n
    This class has attributes and methods that mimic the SMBus class
    but are implemented in a way to allow for testing.
    """

    MEM_R_CH1_H = 8
    MEM_R_CH1_L = 9
    MEM_R_CH2_H = 10
    MEM_R_CH2_L = 11
    MEM_R_CH3_H = 12
    MEM_R_CH3_L = 13
    MEM_R_CH4_H = 14
    MEM_R_CH4_L = 15
    MEM_R_CH5_H = 16
    MEM_R_CH5_L = 17
    MEM_R_CH6_H = 18
    MEM_R_CH6_L = 19

    # Initialize attributes needed for testing
    def __init__(self, bus: int = 1) -> None:
        self._bus = bus
        self._byte_data = bytearray(
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )

    # Override the read_byte_data method to return the byte data
    def read_byte_data(
        self, I2C_addr: int = 1, register: int = 0, force: bool = False
    ) -> int:
        return self._byte_data[register]

    # Override the read_i2c_block_data method to return the byte data
    def read_i2c_block_data(
        self,
        I2C_addr: int = 1,
        register: int = 0,
        length: int = 10,
        force: bool = False,
    ) -> list[int]:
        data = []
        for i in range(length):
            data.append(int(self._byte_data[i]))
        return data


class MockStrainAmp(StrainAmp):
    """
    Create a mock StrainAmp class to test the StrainAmp and Loadcell classes\n
    This class inherits from the StrainAmp class but overrides the _SMBus atttribute
    with a MockSMBus object.
    """

    def __init__(self, bus: int = 1, I2C_addr=0x66) -> None:
        self._SMBus = MockSMBus(bus=bus)
        self.bus = bus
        self.addr = I2C_addr
        self.genvars = np.zeros((3, 6))
        self.indx = 0
        self.is_streaming = True
        self.data = []
        self.failed_reads = 0


class MockLoadcell(Loadcell):
    """
    Create a mock Loadcell class to test the StrainAmp and Loadcell classes\n
    This class inherits from the Loadcell class but overrides the _lc atttribute
    with a MockStrainAmp object.
    """

    # Initialize the same way but with a mock StrainAmp
    def __init__(
        self,
        dephy_mode: bool = False,
        joint: Joint = None,  # type: ignore
        amp_gain: float = 125.0,
        exc: float = 5.0,
        loadcell_matrix: np.ndarray = LOADCELL_MATRIX,
        logger: "Logger" = None,  # type: ignore
        bus: int = 1,
    ) -> None:
        self._is_dephy: bool = dephy_mode
        self._joint: Joint = joint
        self._amp_gain: float = amp_gain
        self._exc: float = exc
        self._adc_range: int = 2**12 - 1
        self._offset: float = (2**12) / 2
        self._lc = None

        if not self._is_dephy:
            self._lc = MockStrainAmp()

        self._loadcell_matrix = loadcell_matrix
        self._loadcell_data = None
        self._prev_loadcell_data = None

        self._loadcell_zero = np.zeros(shape=(1, 6), dtype=np.double)
        self._zeroed = False
        self._log: Logger = logger


@pytest.fixture
def strainamp_mock() -> MockStrainAmp:
    """
    Fixture which returns a MockStrainAmp object
    """

    return MockStrainAmp()


@pytest.fixture
def patch_strainamp(mocker, strainamp_mock: MockStrainAmp):
    """
    Fixture which patches the StrainAmp class to return a MockStrainAmp object
    """

    mocker.patch(
        "opensourceleg.hardware.sensors.StrainAmp.__new__", return_value=strainamp_mock
    )


@pytest.fixture
def strainamp_patched(patch_strainamp) -> StrainAmp:
    """
    Fixture which returns a patched StrainAmp object
    """

    obj = StrainAmp(bus=1)
    return obj


@pytest.fixture
def loadcell_mock() -> MockLoadcell:
    """
    Fixture which returns a MockLoadcell object
    """

    return MockLoadcell()


@pytest.fixture
def patch_loadcell(mocker, loadcell_mock: MockLoadcell):
    """
    Fixture which patches the Loadcell class to return a MockLoadcell object
    """

    mocker.patch(
        "opensourceleg.hardware.sensors.Loadcell.__new__", return_value=loadcell_mock
    )


@pytest.fixture
def loadcell_patched(patch_loadcell) -> Loadcell:
    """
    Fixture which returns a patched Loadcell object
    """

    obj = Loadcell()
    return obj


@pytest.fixture
def patch_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")


def test_mockstrainamp_init():
    """
    Test the MockStrainAmp constructor\n
    This test initializes a MockStrainAmp object and asserts the attributes are initialized properly.
    """

    test_mockstrainamp_default = MockStrainAmp(bus=1)
    # Assert the attributes are initialized properly
    assert test_mockstrainamp_default.MEM_R_CH1_H == 8
    assert test_mockstrainamp_default.MEM_R_CH1_L == 9
    assert test_mockstrainamp_default.MEM_R_CH2_H == 10
    assert test_mockstrainamp_default.MEM_R_CH2_L == 11
    assert test_mockstrainamp_default.MEM_R_CH3_H == 12
    assert test_mockstrainamp_default.MEM_R_CH3_L == 13
    assert test_mockstrainamp_default.MEM_R_CH4_H == 14
    assert test_mockstrainamp_default.MEM_R_CH4_L == 15
    assert test_mockstrainamp_default.MEM_R_CH5_H == 16
    assert test_mockstrainamp_default._SMBus._bus == 1
    assert test_mockstrainamp_default._SMBus._byte_data == bytearray(
        [0 for i in range(20)]
    )
    assert test_mockstrainamp_default.bus == 1
    assert test_mockstrainamp_default.addr == 0x66
    assert np.array_equal(test_mockstrainamp_default.genvars, np.zeros((3, 6)))
    assert test_mockstrainamp_default.indx == 0
    assert test_mockstrainamp_default.is_streaming == True
    assert test_mockstrainamp_default.data == []
    assert test_mockstrainamp_default.failed_reads == 0


def test_strainamp_read_byte_data():
    """
    Test the StrainAmp read_byte_data method\n
    This test initializes a MockSMBus object and calls the read_byte_data method
    and asserts the proper values are returned.
    """

    smbus_mock = MockSMBus()
    # Assert the default value is 0
    assert smbus_mock.read_byte_data() == 0
    smbus_mock._byte_data[0] = 1
    smbus_mock._byte_data[1] = 2
    smbus_mock._byte_data[2] = 3
    smbus_mock._byte_data[3] = 4
    # Assert the proper values are returned
    assert smbus_mock.read_byte_data(register=0) == 1
    assert smbus_mock.read_byte_data(register=1) == 2
    assert smbus_mock.read_byte_data(register=2) == 3
    assert smbus_mock.read_byte_data(register=3) == 4


def test_strainamp_read_compressed_strain(strainamp_patched: StrainAmp):
    """
    Test the StrainAmp read_compressed_strain method\n
    This test initializes a StrainAmp object with byte array data and calls the
    read_compressed_strain method and asserts the proper array is returned.
    """

    # Initialize the StrainAmp object with byte array data
    msa_rcs = strainamp_patched
    msa_rcs._SMBus._byte_data = bytearray(
        [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A]
    )
    # Calculate the expected values by hand
    expected_data = [16, 515, 64, 1286, 112, 2057]
    compressed_strain = msa_rcs._read_compressed_strain()
    # Assert the proper array is returned
    assert np.array_equal(compressed_strain, expected_data)


def test_strainamp_update(strainamp_patched: StrainAmp):
    """
    Test the StrainAmp update method\n
    This test initializes a StrainAmp object with byte array data and calls the
    update method and asserts the proper array is returned and the index is updated properly.
    The update method is called again and the proper array is returned and the index is updated properly.
    The update method is called again and the proper array is returned and the index is updated properly.
    """

    # Initialize the StrainAmp object with byte array data
    msa_update = strainamp_patched
    msa_update._SMBus._byte_data = bytearray(
        [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A]
    )
    # Call the update method and assert the new index is updated properly and the proper array is returned
    actual_array = msa_update.update()
    expected_array = np.array([16, 515, 64, 1286, 112, 2057])
    assert np.array_equal(actual_array, expected_array)


def test_strainamp_unpack_uncompressed_strain():
    """
    Test the StrainAmp unpack_uncompressed_strain method\n
    This test initializes a StrainAmp object with byte array data and calls the
    unpack_uncompressed_strain method and asserts the proper array is returned.
    """

    # Initialize the data to be unpacked
    byte_data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C]
    # Call the static method and assert the proper array is returned
    unpacked_strain = MockStrainAmp._unpack_uncompressed_strain(byte_data)
    assert np.array_equal(unpacked_strain, [258, 772, 1286, 1800, 2314, 2828])


def test_strainamp_unpack_compressed_strain():
    """
    Test the StrainAmp unpack_compressed_strain method\n
    This test initializes byte_data and calls the unpack_compressed_strain
    static method and asserts the proper array is returned.
    """

    # Initialize the data to be unpacked
    byte_data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09]
    # Call the static method and assert the proper array is returned
    unpacked_strain = MockStrainAmp._unpack_compressed_strain(byte_data)
    assert np.array_equal(unpacked_strain, [16, 515, 64, 1286, 112, 2057])


def test_mockloadcell_init():
    """
    Test the MockLoadcell constructor\n
    This test initializes a MockLoadcell object and asserts the attributes are initialized properly.
    """

    # Initialize the MockLoadcell object and assert the attributes are initialized properly
    test_loadcell_default = MockLoadcell()
    assert test_loadcell_default._is_dephy == False
    assert test_loadcell_default._joint == None
    assert test_loadcell_default._amp_gain == 125.0
    assert test_loadcell_default._exc == 5.0
    assert test_loadcell_default._adc_range == 2**12 - 1
    assert test_loadcell_default._offset == (2**12) / 2
    assert test_loadcell_default._lc != None
    assert np.array_equal(test_loadcell_default._loadcell_matrix, LOADCELL_MATRIX)
    assert test_loadcell_default._loadcell_data == None
    assert test_loadcell_default._prev_loadcell_data == None
    assert np.array_equal(
        test_loadcell_default._loadcell_zero, np.zeros(shape=(1, 6), dtype=np.double)
    )
    assert test_loadcell_default._zeroed == False
    assert test_loadcell_default._log == None


def test_loadcell_default_properties(loadcell_patched: Loadcell):
    """
    Test the Loadcell default properties\n
    This test initializes a Loadcell object and asserts the default properties are all zero.
    """

    # Initialize the Loadcell object and assert the default properties are all zero
    loadcell_default = loadcell_patched
    assert loadcell_default.is_zeroed == False
    assert loadcell_default.fx == 0.0
    assert loadcell_default.fy == 0.0
    assert loadcell_default.fz == 0.0
    assert loadcell_default.mx == 0.0
    assert loadcell_default.my == 0.0
    assert loadcell_default.mz == 0.0
    assert loadcell_default.loadcell_data == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_loadcell_nondefault_properties(loadcell_patched: Loadcell):
    """
    Test the Loadcell non-default properties\n
    This test initializes a Loadcell object and passes non-zero data to the _loadcell_data attribute
    and asserts the properties are correctly non-zero.
    """

    # Initialize the Loadcell object and pass non-zero data to the _loadcell_data attribute
    loadcell_nondefault = loadcell_patched
    loadcell_nondefault._zeroed = True
    loadcell_nondefault._loadcell_data = [
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
        [13.0, 14.0, 15.0, 16.0, 17.0, 18.0],
        [19.0, 20.0, 21.0, 22.0, 23.0, 24.0],
        [25.0, 26.0, 27.0, 28.0, 29.0, 30.0],
        [31.0, 32.0, 33.0, 34.0, 35.0, 36.0],
    ]
    # Assert the properties are correctly non-zero
    assert loadcell_nondefault.is_zeroed == True
    assert loadcell_nondefault.fx == 1.0
    assert loadcell_nondefault.fy == 2.0
    assert loadcell_nondefault.fz == 3.0
    assert loadcell_nondefault.mx == 4.0
    assert loadcell_nondefault.my == 5.0
    assert loadcell_nondefault.mz == 6.0
    assert loadcell_nondefault.loadcell_data == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_loadcell_reset(loadcell_patched: Loadcell):
    """
    Test the Loadcell reset method\n
    This test initializes a Loadcell object and passes non-zero data to the _loadcell_data attribute
    and asserts the reset method correctly resets the attributes.
    """

    # Initialize the Loadcell object and pass non-zero data to the _loadcell_data attribute
    loadcell_reset = loadcell_patched
    loadcell_reset._zeroed = True
    loadcell_reset._loadcell_zero = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]
    loadcell_reset.reset()
    # Assert the reset method correctly resets the attributes
    assert loadcell_reset._zeroed == False
    assert np.array_equal(
        loadcell_reset._loadcell_zero, np.zeros(shape=(1, 6), dtype=np.double)
    )


def test_loadcell_update(loadcell_patched: Loadcell):
    """
    Test the Loadcell update method\n
    This test initializes a Loadcell object and passes data into attributes needed for testing
    and calls the update method and asserts the proper values are returned. These expected
    values are calculated by hand. This process is then repeated for both if/else statements.
    """

    # Initialize the Loadcell object and pass data into attributes needed for testing
    loadcell_update = loadcell_patched
    loadcell_update._is_dephy = True
    loadcell_update._joint = MockJoint()
    loadcell_update._joint._data = Data(
        genvar_0=1, genvar_1=2, genvar_2=3, genvar_3=4, genvar_4=5, genvar_5=6
    )
    # Call the update method and assert the proper values are returned
    # This iteration triggers the first if statement and the seconde if statement
    loadcell_update.update()
    # Calculate the intermediate values "by hand"
    loadcell_coupled = [
        ((1 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((2 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((3 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((4 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((5 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((6 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
    ]
    loadcell_signed = [
        [
            loadcell_coupled[0] * -35.44949,
            loadcell_coupled[0] * -1408.27600,
            loadcell_coupled[0] * 5.28557,
            loadcell_coupled[0] * -14.07667,
            loadcell_coupled[0] * 19.88193,
            loadcell_coupled[0] * 1413.95837,
        ],
        [
            loadcell_coupled[1] * -3.48398,
            loadcell_coupled[1] * 821.60516,
            loadcell_coupled[1] * -51.38681,
            loadcell_coupled[1] * -1630.13098,
            loadcell_coupled[1] * 42.46563,
            loadcell_coupled[1] * 823.29095,
        ],
        [
            loadcell_coupled[2] * -817.61768,
            loadcell_coupled[2] * -2.21026,
            loadcell_coupled[2] * -840.11005,
            loadcell_coupled[2] * -8.60509,
            loadcell_coupled[2] * -831.32318,
            loadcell_coupled[2] * -3.53086,
        ],
        [
            loadcell_coupled[3] * 17.09737,
            loadcell_coupled[3] * 0.17497,
            loadcell_coupled[3] * 0.22292,
            loadcell_coupled[3] * -0.58087,
            loadcell_coupled[3] * -16.93312,
            loadcell_coupled[3] * -0.05286,
        ],
        [
            loadcell_coupled[4] * -9.28386,
            loadcell_coupled[4] * -0.30000,
            loadcell_coupled[4] * 20.22296,
            loadcell_coupled[4] * -0.07903,
            loadcell_coupled[4] * -9.65388,
            loadcell_coupled[4] * 0.34513,
        ],
        [
            loadcell_coupled[5] * -0.61599,
            loadcell_coupled[5] * -21.24456,
            loadcell_coupled[5] * -0.50275,
            loadcell_coupled[5] * 21.10707,
            loadcell_coupled[5] * -0.80625,
            loadcell_coupled[5] * -23.02333,
        ],
    ]
    loadcell_signed_added_and_transposed = [
        [
            loadcell_signed[0][0]
            + loadcell_signed[0][1]
            + loadcell_signed[0][2]
            + loadcell_signed[0][3]
            + loadcell_signed[0][4]
            + loadcell_signed[0][5],
            loadcell_signed[1][0]
            + loadcell_signed[1][1]
            + loadcell_signed[1][2]
            + loadcell_signed[1][3]
            + loadcell_signed[1][4]
            + loadcell_signed[1][5],
            loadcell_signed[2][0]
            + loadcell_signed[2][1]
            + loadcell_signed[2][2]
            + loadcell_signed[2][3]
            + loadcell_signed[2][4]
            + loadcell_signed[2][5],
            loadcell_signed[3][0]
            + loadcell_signed[3][1]
            + loadcell_signed[3][2]
            + loadcell_signed[3][3]
            + loadcell_signed[3][4]
            + loadcell_signed[3][5],
            loadcell_signed[4][0]
            + loadcell_signed[4][1]
            + loadcell_signed[4][2]
            + loadcell_signed[4][3]
            + loadcell_signed[4][4]
            + loadcell_signed[4][5],
            loadcell_signed[5][0]
            + loadcell_signed[5][1]
            + loadcell_signed[5][2]
            + loadcell_signed[5][3]
            + loadcell_signed[5][4]
            + loadcell_signed[5][5],
        ],
        [0, 0, 0, 0, 0, 0],
    ]
    # Assert the proper values are returned with a couple significant figures
    assert round(loadcell_update.fx, -2) == round(
        loadcell_signed_added_and_transposed[0][0], -2
    )
    assert round(loadcell_update.fy) == round(
        loadcell_signed_added_and_transposed[0][1]
    )
    assert round(loadcell_update.fz, -1) == round(
        loadcell_signed_added_and_transposed[0][2], -1
    )
    assert round(loadcell_update.mx) == round(
        loadcell_signed_added_and_transposed[0][3]
    )
    assert round(loadcell_update.my) == round(
        loadcell_signed_added_and_transposed[0][4]
    )
    assert round(loadcell_update.mz) == round(
        loadcell_signed_added_and_transposed[0][5]
    )

    # This iteration triggers the first if statement and the second else statement
    loadcell_update_loadcell_zero = loadcell_patched
    loadcell_update_loadcell_zero._is_dephy = True
    loadcell_update_loadcell_zero._joint = MockJoint()
    loadcell_update_loadcell_zero._joint._data = Data(
        genvar_0=1, genvar_1=2, genvar_2=3, genvar_3=4, genvar_4=5, genvar_5=6
    )
    loadcell_update_loadcell_zero.update(
        loadcell_zero=np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]])
    )

    assert round(loadcell_update_loadcell_zero.fx, -2) == round(
        loadcell_signed_added_and_transposed[0][0] - 1.0, -2
    )
    assert round(loadcell_update_loadcell_zero.fy) == round(
        loadcell_signed_added_and_transposed[0][1] - 2.0
    )
    assert round(loadcell_update_loadcell_zero.fz, -1) == round(
        loadcell_signed_added_and_transposed[0][2] - 3.0, -1
    )
    assert round(loadcell_update_loadcell_zero.mx) == round(
        loadcell_signed_added_and_transposed[0][3] - 4.0
    )
    assert round(loadcell_update_loadcell_zero.my) == round(
        loadcell_signed_added_and_transposed[0][4] - 5.0
    )
    assert round(loadcell_update_loadcell_zero.mz) == round(
        loadcell_signed_added_and_transposed[0][5] - 6.0
    )

    # This iteration triggers the first else statement and the second else statement
    loadcell_strainamp_update = loadcell_patched
    loadcell_strainamp_update._is_dephy = False
    loadcell_strainamp_update._lc._SMBus._byte_data = bytearray(
        [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A]
    )
    t1 = loadcell_strainamp_update._lc.update()
    t2 = loadcell_strainamp_update._lc.update()
    loadcell_strainamp_update.update(loadcell_zero=np.array([[0, 0, 0, 0, 0, 0]]))
    updated_array = np.array([16, 515, 64, 1286, 112, 2057])
    loadcell_signed1 = (updated_array - 2**12 / 2) / (2**12 - 1) * 5.0
    loadcell_coupled1 = loadcell_signed1 * 1000 / (5.0 * 125.0)
    loadcell_coupled2 = [
        -3.96971917,
        -2.99487179,
        -3.87594628,
        -1.48864469,
        -3.78217338,
        0.01758242,
    ]
    loadcell_signed_dot = [
          [
            loadcell_coupled2[0] * -35.44949,
            loadcell_coupled2[0] * -1408.27600,
            loadcell_coupled2[0] * 5.28557,
            loadcell_coupled2[0] * -14.07667,
            loadcell_coupled2[0] * 19.88193,
            loadcell_coupled2[0] * 1413.95837,
        ],
        [
            loadcell_coupled2[1] * -3.48398,
            loadcell_coupled2[1] * 821.60516,
            loadcell_coupled2[1] * -51.38681,
            loadcell_coupled2[1] * -1630.13098,
            loadcell_coupled2[1] * 42.46563,
            loadcell_coupled2[1] * 823.29095,
        ],
        [
            loadcell_coupled2[2] * -817.61768,
            loadcell_coupled2[2] * -2.21026,
            loadcell_coupled2[2] * -840.11005,
            loadcell_coupled2[2] * -8.60509,
            loadcell_coupled2[2] * -831.32318,
            loadcell_coupled2[2] * -3.53086,
        ],
        [
            loadcell_coupled2[3] * 17.09737,
            loadcell_coupled2[3] * 0.17497,
            loadcell_coupled2[3] * 0.22292,
            loadcell_coupled2[3] * -0.58087,
            loadcell_coupled2[3] * -16.93312,
            loadcell_coupled2[3] * -0.05286,
        ],
        [
            loadcell_coupled2[4] * -9.28386,
            loadcell_coupled2[4] * -0.30000,
            loadcell_coupled2[4] * 20.22296,
            loadcell_coupled2[4] * -0.07903,
            loadcell_coupled2[4] * -9.65388,
            loadcell_coupled2[4] * 0.34513,
        ],
        [
            loadcell_coupled2[5] * -0.61599,
            loadcell_coupled2[5] * -21.24456,
            loadcell_coupled2[5] * -0.50275,
            loadcell_coupled2[5] * 21.10707,
            loadcell_coupled2[5] * -0.80625,
            loadcell_coupled2[5] * -23.02333,
        ],
    ]
    loadcell_signed_dot_added_and_transposed = [
        [
            loadcell_signed_dot[0][0]
            + loadcell_signed_dot[0][1]
            + loadcell_signed_dot[0][2]
            + loadcell_signed_dot[0][3]
            + loadcell_signed_dot[0][4]
            + loadcell_signed_dot[0][5],
            loadcell_signed_dot[1][0]
            + loadcell_signed_dot[1][1]
            + loadcell_signed_dot[1][2]
            + loadcell_signed_dot[1][3]
            + loadcell_signed_dot[1][4]
            + loadcell_signed_dot[1][5],
            loadcell_signed_dot[2][0]
            + loadcell_signed_dot[2][1]
            + loadcell_signed_dot[2][2]
            + loadcell_signed_dot[2][3]
            + loadcell_signed_dot[2][4]
            + loadcell_signed_dot[2][5],
            loadcell_signed_dot[3][0]
            + loadcell_signed_dot[3][1]
            + loadcell_signed_dot[3][2]
            + loadcell_signed_dot[3][3]
            + loadcell_signed_dot[3][4]
            + loadcell_signed_dot[3][5],
            loadcell_signed_dot[4][0]
            + loadcell_signed_dot[4][1]
            + loadcell_signed_dot[4][2]
            + loadcell_signed_dot[4][3]
            + loadcell_signed_dot[4][4]
            + loadcell_signed_dot[4][5],
            loadcell_signed_dot[5][0]
            + loadcell_signed_dot[5][1]
            + loadcell_signed_dot[5][2]
            + loadcell_signed_dot[5][3]
            + loadcell_signed_dot[5][4]
            + loadcell_signed_dot[5][5],
        ],
        [0, 0, 0, 0, 0, 0],
    ]
    assert round(loadcell_strainamp_update.fx, -5) == round(
        loadcell_signed_dot_added_and_transposed[0][0], -5
    )
    assert round(loadcell_strainamp_update.fy, -3) == round(
        loadcell_signed_dot_added_and_transposed[0][1], -3
    )
    assert round(loadcell_strainamp_update.fz, -3) == round(
        loadcell_signed_dot_added_and_transposed[0][2], -3
    )
    assert round(loadcell_strainamp_update.mx, -1) == round(
        loadcell_signed_dot_added_and_transposed[0][3], -1
    )
    assert round(loadcell_strainamp_update.my, -1) == round(
        loadcell_signed_dot_added_and_transposed[0][4], -1
    )
    assert round(loadcell_strainamp_update.mz, -3) == round(
        loadcell_signed_dot_added_and_transposed[0][5], -3
    )


def test_loadcell_initialize(
    loadcell_patched: Loadcell, mocker, patch_sleep, patch_input
):
    """
    Tests the Loadcell initialize method\n
    This test initializes a Loadcell object and passes data into attributes needed for testing
    and calls the initialize method and asserts the proper log messages are written for the
    if statement in the if statement in the if statement. This process is then repeated for
    the else statement in the if statement in the if statement.
    """

    # Initialize the Loadcell object and pass data into attributes needed for testing
    lc_initialize = loadcell_patched
    lc_initialize._log = Logger(
        file_path="tests/test_sensors/test_loadcell_initialize_log"
    )
    lc_initialize._log.set_stream_level("DEBUG")
    lc_initialize._joint = MockJoint()
    lc_initialize._joint.is_streaming = False
    lc_initialize._is_dephy = True
    lc_initialize._zeroed = True
    # Patch the input method to return "y" when running pytest
    # mocker.patch("builtins.input", return_value="y")
    lc_initialize.calibrate(reset=True)
    # Assert the proper log messages are written for the else statement in the if statement in the if statement
    with open("tests/test_sensors/test_loadcell_initialize_log.log") as f:
        contents = f.read()
        assert (
            "INFO: [Loadcell] Initiating zeroing routine, please ensure that there is no ground contact force."
            in contents
        )
        assert (
            "WARNING: [Loadcell] knee joint isn't streaming data. Please start streaming data before initializing loadcell."
            in contents
        )
    # Assigning attibutes to test the if statement in the if statement in the if statement
    lc_initialize._joint.is_streaming = True
    lc_initialize._joint._data = Data(
        mot_cur=13,
        temperature=12,
        genvar_0=1,
        genvar_1=2,
        genvar_2=3,
        genvar_3=4,
        genvar_4=5,
        genvar_5=6,
    )
    lc_initialize.calibrate(number_of_iterations=1)
    # Assert the data was properly updated
    assert lc_initialize._zeroed == True
    assert lc_initialize._joint._data.batt_volt == 15
    assert lc_initialize._joint._data.batt_curr == 15
    assert lc_initialize._joint._data.mot_volt == 15
    assert lc_initialize._joint._data.mot_cur == 28
    assert lc_initialize._joint._data.mot_ang == 15
    assert lc_initialize._joint._data.ank_ang == 15
    assert lc_initialize._joint._data.mot_vel == 15
    assert lc_initialize._joint._data.mot_acc == 15
    assert lc_initialize._joint._data.ank_vel == 15
    assert lc_initialize._joint._data.temperature == 27
    assert lc_initialize._joint._data.genvar_0 == 16
    assert lc_initialize._joint._data.genvar_1 == 17
    assert lc_initialize._joint._data.genvar_2 == 18
    assert lc_initialize._joint._data.genvar_3 == 19
    assert lc_initialize._joint._data.genvar_4 == 20
    assert lc_initialize._joint._data.genvar_5 == 21
    assert lc_initialize._joint._data.accelx == 15
    assert lc_initialize._joint._data.accely == 15
    assert lc_initialize._joint._data.accelz == 15
    assert lc_initialize._joint._data.gyrox == 15
    assert lc_initialize._joint._data.gyroy == 15
    assert lc_initialize._joint._data.gyroz == 15
    assert (
        lc_initialize._joint._thermal_model.T_w
        == (
            (
                (((28 * 1e-3) ** 2) * 0.376 * (1 + 0.393 / 100 * (21 - 65)))
                + (27 - 21) / 1.0702867186480716
            )
            / (0.20 * 81.46202695970649)
        )
        / 500
        + 21
    )
    assert (
        lc_initialize._joint._thermal_model.T_c
        == ((21 - 27) / 1.0702867186480716 + (21 - 27) / 1.9406620046327363)
        / 512.249065845453
        / 500
        + 27
    )
    # Calculate the intermediate values "by hand"
    loadcell_coupled = [
        ((16 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((17 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((18 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((19 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((20 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
        ((21 - (2**12) / 2) / (2**12 - 1) * 5.0) * 1000 / (5.0 * 125.0),
    ]
    loadcell_signed = [
        [
            loadcell_coupled[0] * -35.44949,
            loadcell_coupled[0] * -1408.27600,
            loadcell_coupled[0] * 5.28557,
            loadcell_coupled[0] * -14.07667,
            loadcell_coupled[0] * 19.88193,
            loadcell_coupled[0] * 1413.95837,
        ],
        [
            loadcell_coupled[1] * -3.48398,
            loadcell_coupled[1] * 821.60516,
            loadcell_coupled[1] * -51.38681,
            loadcell_coupled[1] * -1630.13098,
            loadcell_coupled[1] * 42.46563,
            loadcell_coupled[1] * 823.29095,
        ],
        [
            loadcell_coupled[2] * -817.61768,
            loadcell_coupled[2] * -2.21026,
            loadcell_coupled[2] * -840.11005,
            loadcell_coupled[2] * -8.60509,
            loadcell_coupled[2] * -831.32318,
            loadcell_coupled[2] * -3.53086,
        ],
        [
            loadcell_coupled[3] * 17.09737,
            loadcell_coupled[3] * 0.17497,
            loadcell_coupled[3] * 0.22292,
            loadcell_coupled[3] * -0.58087,
            loadcell_coupled[3] * -16.93312,
            loadcell_coupled[3] * -0.05286,
        ],
        [
            loadcell_coupled[4] * -9.28386,
            loadcell_coupled[4] * -0.30000,
            loadcell_coupled[4] * 20.22296,
            loadcell_coupled[4] * -0.07903,
            loadcell_coupled[4] * -9.65388,
            loadcell_coupled[4] * 0.34513,
        ],
        [
            loadcell_coupled[5] * -0.61599,
            loadcell_coupled[5] * -21.24456,
            loadcell_coupled[5] * -0.50275,
            loadcell_coupled[5] * 21.10707,
            loadcell_coupled[5] * -0.80625,
            loadcell_coupled[5] * -23.02333,
        ],
    ]
    loadcell_signed_dot_added_and_transposed = [
        [
            loadcell_signed[0][0]
            + loadcell_signed[0][1]
            + loadcell_signed[0][2]
            + loadcell_signed[0][3]
            + loadcell_signed[0][4]
            + loadcell_signed[0][5],
            loadcell_signed[1][0]
            + loadcell_signed[1][1]
            + loadcell_signed[1][2]
            + loadcell_signed[1][3]
            + loadcell_signed[1][4]
            + loadcell_signed[1][5],
            loadcell_signed[2][0]
            + loadcell_signed[2][1]
            + loadcell_signed[2][2]
            + loadcell_signed[2][3]
            + loadcell_signed[2][4]
            + loadcell_signed[2][5],
            loadcell_signed[3][0]
            + loadcell_signed[3][1]
            + loadcell_signed[3][2]
            + loadcell_signed[3][3]
            + loadcell_signed[3][4]
            + loadcell_signed[3][5],
            loadcell_signed[4][0]
            + loadcell_signed[4][1]
            + loadcell_signed[4][2]
            + loadcell_signed[4][3]
            + loadcell_signed[4][4]
            + loadcell_signed[4][5],
            loadcell_signed[5][0]
            + loadcell_signed[5][1]
            + loadcell_signed[5][2]
            + loadcell_signed[5][3]
            + loadcell_signed[5][4]
            + loadcell_signed[5][5],
        ],
        [0, 0, 0, 0, 0, 0],
    ]
    # Assert the proper values are returned with a couple significant figures
    assert round(lc_initialize.fx, -2) == round(
        loadcell_signed_dot_added_and_transposed[0][0], -2
    )
    assert round(lc_initialize.fy, -2) == round(
        loadcell_signed_dot_added_and_transposed[0][1], -2
    )
    assert round(lc_initialize.fz, -2) == round(
        loadcell_signed_dot_added_and_transposed[0][2], -2
    )
    assert round(lc_initialize.mx) == round(
        loadcell_signed_dot_added_and_transposed[0][3]
    )
    assert round(lc_initialize.my) == round(
        loadcell_signed_dot_added_and_transposed[0][4]
    )
    assert round(lc_initialize.mz) == round(
        loadcell_signed_dot_added_and_transposed[0][5]
    )
    # Assigning attibutes to test the else statement in the if statement
    lc_initialize_else = loadcell_patched
    lc_initialize_else._zeroed = False
    lc_initialize_else._is_dephy = False
    lc_initialize_else._joint = MockJoint()
    lc_initialize_else._joint._data = Data(
        mot_cur=13,
        temperature=12,
        genvar_0=1,
        genvar_1=2,
        genvar_2=3,
        genvar_3=4,
        genvar_4=5,
        genvar_5=6,
    )
    lc_initialize_else.calibrate(number_of_iterations=1)
    # Assert the proper values are returned with a couple significant figures
    assert round(lc_initialize_else.fx, -2) == round(
        loadcell_signed_dot_added_and_transposed[0][0], -2
    )
    assert round(lc_initialize_else.fy, -3) == round(
        loadcell_signed_dot_added_and_transposed[0][1], -3
    )
    assert round(lc_initialize_else.fz, -3) == round(
        loadcell_signed_dot_added_and_transposed[0][2], -3
    )
    assert round(lc_initialize_else.mx) == round(
        loadcell_signed_dot_added_and_transposed[0][3]
    )
    assert round(lc_initialize_else.my) == round(
        loadcell_signed_dot_added_and_transposed[0][4]
    )
    assert round(lc_initialize_else.mz, -1) == round(
        loadcell_signed_dot_added_and_transposed[0][5], -1
    )

import faulthandler, sys
faulthandler.enable()
import pytest
sys.exit(pytest.main())
